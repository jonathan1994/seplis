import urllib.parse
import logging
import copy
import time
from seplis.decorators import new_session, auto_session, auto_pipe
from seplis.connections import database
from seplis import utils
from seplis.api.base.pagination import Pagination
from seplis.api.base.description import Description
from seplis.api.base.user import Users
from seplis.api import exceptions, constants, models
from datetime import datetime, timedelta
from sqlalchemy import asc, and_

class Show(object):

    def __init__(self, id, title, description, premiered, ended, 
                 externals, indices, status, runtime, genres,
                 alternate_titles, seasons, fans, updated=None):
        '''

        :param id: int
        :param title: str
        :param description: `seplis.api.description.description()`
        :param premiered: `datetime.date()`
        :param ended: `datetime.date()`
        :param externals: `dict()`
            {
                'name': 'value1
            }
        :param indices: `dict()`
            {
                'index': 'value'
            }
        :param status: int
        :param runtime: int
        :param genres: list of str
        :param alternate_titles: list of str
        :param seasons: list of dict
        :param fans: int
        :param updated: datetime
        '''
        self.id = id
        self.title = title
        self.description = description
        self.premiered = premiered
        self.ended = ended
        if not externals:
            externals = {}
        self.externals = externals
        if not indices:
            indices = {}
        self.indices = indices
        self.status = status
        self.runtime = runtime
        self.genres = genres
        self.alternate_titles = alternate_titles
        self.seasons = seasons
        self.updated = updated
        self.fans = fans

    @auto_session
    @auto_pipe
    def save(self, session=None, pipe=None):
        self._check_index()
        self.updated = datetime.utcnow()
        self.seasons = self._count_season_episodes(session)
        session.query(
            models.Show,
        ).filter(
            models.Show.id == self.id,
        ).update({
            'title': self.title,
            'description_text': self.description.text,
            'description_title': self.description.title,
            'description_url': self.description.url,
            'premiered': self.premiered,
            'ended': self.ended,
            'index_info': self.indices.get('info') if self.indices else None,
            'index_episodes': self.indices.get('episodes') if self.indices else None,
            'externals': self.externals,
            'status': self.status,
            'runtime': self.runtime,
            'genres': self.genres,
            'alternate_titles': self.alternate_titles,
            'updated': self.updated,
            'seasons': self.seasons,
        })
        self.update_external(
            pipe=pipe,
            session=session,
            overwrite=True,
        )
        self.to_elasticsearch()

    @classmethod
    def _format_from_row(cls, row):
        if not row:
            return None
        obj = cls(
            id=row.id,
            title=row.title,
            description=Description(
                text=row.description_text,
                title=row.description_title,
                url=row.description_url,
            ),
            premiered=row.premiered,
            ended=row.ended,
            indices={
                'info': row.index_info,
                'episodes': row.index_episodes,
            },
            externals=row.externals if row.externals else {},
            status=row.status,
            runtime=row.runtime,
            genres=row.genres if row.genres else [],
            alternate_titles=row.alternate_titles if row.alternate_titles else [],
            seasons=row.seasons if row.seasons else [],
            fans=row.fans,
            updated=row.updated,
        )
        return obj

    @classmethod
    @auto_session
    def get(cls, id_, session=None):
        '''

        :param id_: int
        :param session: SQLAlchemy session
        :returns: `Show()`
        '''
        show = session.query(
            models.Show,
        ).filter(
            models.Show.id == id_,
        ).first()
        if not show:
            return None
        return cls._format_from_row(show)

    @classmethod
    @auto_session
    def create(cls, session):        
        '''
        Creates a new show and returns the id.

        :param session: sqlalchemy session
        :returns: int
        '''
        show = models.Show(
            created=datetime.utcnow(),
        )
        session.add(show)
        session.flush()
        return show.id

    def to_dict(self):
        return self.__dict__

    def to_elasticsearch(self):
        '''

        :returns: boolean
        '''
        database.es.index(
            index='shows',
            doc_type='show',
            id=self.id,
            body=utils.json_dumps(self),
        )

    def _check_index(self):
        '''
        Checks that the index value is in the externals. 

        :param show: `Show()`
        :raises: `exceptions.Show_external_field_must_be_specified_exception()`
        :raises: `exceptions.Show_index_type_must_be_in_external_field_exception()`
        '''
        if not self.indices or \
            not self.indices.get('info') and \
                not self.indices.get('episodes'):
            return
        if not self.externals:
            raise exceptions.Show_external_field_must_be_specified_exception()
        for key in self.indices:
            if (self.indices[key] != None) and \
               (self.indices[key] not in self.externals):
                raise exceptions.Show_index_type_must_be_in_external_field_exception(
                    self.indices[key]
                )

    @auto_session
    def _count_season_episodes(self, session=None):
        '''
        Registers `from` and `to` episode numbers per season.
        '''
        rows = session.execute('''
            SELECT 
                season,
                min(number) as `from`,
                max(number) as `to`,
                count(number) as total
            FROM
                episodes
            WHERE
                show_id = :show_id
            GROUP BY season;
        ''', {
            'show_id': self.id,
        })
        seasons = []
        for row in rows:
            if not row['season']:
                continue
            seasons.append({
                'season': row['season'],
                'from': row['from'],
                'to': row['to'],
                'total': row['total'],
            })
        return seasons

    @auto_pipe
    @auto_session
    def become_fan(self, user_id, session=None, pipe=None):
        '''

        :param user_id: int or list of int
        :returns: boolean
        '''
        fan = session.query(
            models.Show_fan,
        ).filter(
            models.Show_fan.show_id == self.id,
            models.Show_fan.user_id == user_id,
        ).first()
        if fan:
            return
        fan = models.Show_fan(
            show_id=self.id,
            user_id=user_id,
        )
        session.add(fan)
        self._incr_fan(
            user_id=user_id,
            incr=1,
            session=session,
            pipe=pipe,
        )
        self.cache_fan(
            show_id=self.id,
            user_id=user_id,
            pipe=pipe,
            incr_count=False,
        )
        return True

    @classmethod
    def cache_fan(cls, show_id, user_id, pipe, incr_count=True):
        pipe.sadd(
            'users:{}:fan_of'.format(user_id), 
            show_id,
        )
        pipe.sadd(
            'shows:{}:fans'.format(show_id), 
            user_id,
        )
        if incr_count:
            pipe.hincrby('shows:{}'.format(show_id), 'fans', 1)
            pipe.hincrby('users:{}'.format(user_id), 'fan_of', 1)

    @auto_pipe
    @auto_session
    def _incr_fan(self, user_id, incr, 
                 session=None, pipe=None):
        session.query(
            models.User,
        ).filter(
            models.User.id == user_id,
        ).update({
            'fan_of': models.User.fan_of + incr,
        })                
        show = session.query(
            models.Show,
        ).filter(
            models.Show.id == self.id,
        ).update({
            'fans': models.Show.fans + incr,
        })            
        self.fans += incr
        database.es.update(
            index='shows',
            doc_type='show',
            id=self.id,
            body={
                'doc': {
                    'fans': self.fans,
                },
            },
        )
        pipe.hincrby('shows:{}'.format(self.id), 'fans', incr)
        pipe.hincrby('users:{}'.format(user_id), 'fan_of', incr)

    @auto_pipe
    @auto_session
    def unfan(self, user_id, session=None, pipe=None):        
        '''

        :param user_id: int or list of int
        :returns: boolean
        '''        
        deleted = session.query(
            models.Show_fan,
        ).filter(
            models.Show_fan.show_id == self.id,
            models.Show_fan.user_id == user_id,
        ).delete()
        if not deleted:
            return False
        self._incr_fan(
            user_id=user_id,
            incr=-1,
            session=session,
            pipe=pipe,
        )
        pipe.srem(
            'users:{}:fan_of'.format(user_id), 
            self.id,
        )
        pipe.srem(
            'shows:{}:fans'.format(self.id), 
            user_id,
        )
        return True

    def update_external(self, session, pipe, overwrite=False):
        '''

        :param session: SQLAlchemy session
        :param pipe: Redis pipe
        :param overwrite: boolean
        '''
        if overwrite:
            externals_query = session.query(
                models.Show_external,
            ).filter(
                models.Show_external.show_id == self.id,
            ).all()
            for external in externals_query:
                name = 'shows:external:{}:{}'.format(
                    urllib.parse.quote(external.title),
                    urllib.parse.quote(external.value),
                )
                pipe.delete(name, self.id)
                session.delete(external)
        for key, value in self.externals.items():
            duplicate_show_id = self.get_id_by_external(key, value)
            if duplicate_show_id and (duplicate_show_id != self.id):
                raise exceptions.Show_external_duplicated(
                    external_title=key,
                    external_id=value,
                    show=self.get(duplicate_show_id),
                )
            external = models.Show_external(
                show_id=self.id,
                title=key,
                value=value,
            )
            self.cache_external(
                pipe=pipe,
                external_title=key,
                external_id=value,
                show_id=self.id,
            )
            session.merge(external)

    def get_fans(self, page=1, per_page=constants.PER_PAGE):
        '''

        :returns: list of `seplis.api.base.pagination.Pagination()`
        '''
        pipe = database.redis.pipeline()
        name = 'shows:{}:fans'.format(self.id)
        pipe.scard(name)
        pipe.sort(
            name=name,
            start=(page - 1) * per_page,
            num=per_page,
            by='nosort',
        )
        total_count, user_ids = pipe.execute()
        return Pagination(
            page=page,
            per_page=per_page,
            total=total_count,
            records=Users.get(user_ids),
        )

    @classmethod
    def cache_external(cls, pipe, external_title, external_id, show_id):
        if not external_id or not external_title:
            return
        name = 'shows:external:{}:{}'.format(
            urllib.parse.quote(external_title),
            urllib.parse.quote(external_id),
        )
        pipe.set(name, show_id)

    @classmethod
    def get_id_by_external(cls, external_title, external_id):
        '''

        :param external_title: str
        :param external_id: str
        '''
        if not external_id or not external_title:
            return
        name = 'shows:external:{}:{}'.format(
            urllib.parse.quote(external_title),
            urllib.parse.quote(external_id),
        )
        show_id = database.redis.get(name)
        if not show_id:
            return
        return int(show_id)

    @classmethod
    def is_fan(cls, user_id, id_):
        name = 'users:{}:fan_of'.format(user_id)
        return database.redis.sismember(name, id_)

class Shows(object):

    sort_lookup = {
        'id': models.Show.id,
        'updated': models.Show.updated,
        'status': models.Show.status,
        'fans': models.Show.fans,
        'title': models.Show.title,
        'premiered': models.Show.premiered,
        'ended': models.Show.ended,
        'runtime': models.Show.runtime,
        'user_watching': {
            'datetime': models.Show_watched.datetime,
            'position': models.Show_watched.position,
        }
    }

    @classmethod
    def is_fan(cls, user_id, ids):
        name = 'users:{}:fan_of'.format(user_id)
        pipe = database.redis.pipeline()
        for id_ in ids:
            pipe.sismember(name, id_)
        return pipe.execute()

    @classmethod
    @auto_session
    def get_fan_of(cls, user_id, per_page=constants.PER_PAGE, 
                   page=1, sort='title:asc', session=None):
        sort = models.sort_parser(sort, cls.sort_lookup)
        query = session.query(
            models.Show_fan,
        ).filter(
            models.Show_fan.user_id == user_id,
            models.Show.id == models.Show_fan.show_id,
        )
        pagination = Pagination.from_query(
            query,
            count_field=models.Show_fan.show_id,
            page=page,
            per_page=per_page,
        )
        query = query.with_entities(
            models.Show_fan,
            models.Show,
            models.Show_watched,
            models.Episode,
        ).outerjoin(
            (models.Show_watched, and_(
                models.Show_watched.show_id == models.Show_fan.show_id,
                models.Show_watched.user_id == models.Show_fan.user_id,
            )),
            (models.Episode, and_(
                models.Episode.show_id == models.Show_watched.show_id,
                models.Episode.number == models.Show_watched.episode_number,
            )),
        )
        query = query.order_by(
            *sort
        )
        query = query.limit(
            int(per_page),
        ).offset(
            int(page-1) * int(per_page),
        )
        shows = []
        for row in query.all():
            show = Show._format_from_row(
                row.Show,
            )
            show.user_watching = None
            if row.Show_watched and row.Episode:
                from seplis.api.base.episode import Episode
                show.user_watching = {
                    'datetime': row.Show_watched.datetime,
                    'position': row.Show_watched.position,
                    'episode': Episode._format_from_row(row.Episode),
                }
            shows.append(
                show
            )
        pagination.records = shows
        return pagination