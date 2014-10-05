from seplis.config import config
from seplis.connections import database

def create_indices():
    database.es.indices.delete('shows', ignore=404)
    database.es.indices.delete('episodes', ignore=404)
    database.es.indices.delete('images', ignore=404)

    settings = {
        'analysis': {
            'filter': {
                'nGram_filter': {
                    'type': 'nGram',
                    'min_gram': 1,
                    'max_gram': 20,
                    'token_chars': [
                        'letter',
                        'digit',
                        'punctuation',
                        'symbol'
                    ]
                }
            },
            'analyzer': {
                'nGram_analyzer': {
                    'type': 'custom',
                    'tokenizer': 'whitespace',
                    'filter': [
                       'lowercase',
                       'asciifolding',
                       'nGram_filter'
                   ]
                },
                'whitespace_analyzer': {
                    'type': 'custom',
                    'tokenizer': 'whitespace',
                    'filter': [
                        'lowercase',
                        'asciifolding'
                   ]
                }
            }
        }
    }

    database.es.indices.create('shows', body={
        'settings': settings,
        'mappings': {
            'show': {
                'properties' : {
                    'title': {
                        'type': 'string',
                        'index_analyzer': 'nGram_analyzer',
                        'search_analyzer': 'whitespace_analyzer',          
                        "fields": {
                            "raw": { 
                                "type": "string",
                                "index": "not_analyzed"
                            }
                        }
                    },
                    'id': { 'type': 'integer' },
                    'description': {
                        'dynamic' : False,
                        'properties' : {
                            'text': { 'type': 'string' },
                            'url': { 'type': 'string' },
                            'title': { 'type': 'string' },
                        }
                    },
                    'premiered': { 'type': 'date' },
                    'ended': { 'type': 'date' },
                    'externals': {
                        'dynamic' : True,
                        'type': 'object',
                    },
                    'indices': {
                        'dynamic': False,
                        'properties': {
                            'info': { 'type': 'string' },
                            'episodes': { 'type': 'string' },
                            'images': { 'type': 'string' },
                        },
                    },
                    'status': { 'type': 'integer' },
                    'runtime': { 'type': 'integer' },
                    'seasons': {
                        'properties': {
                            'season': { 'type': 'integer' },
                            'from': { 'type': 'integer' },
                            'to': { 'type': 'integer' },
                            'total': { 'type': 'integer' },
                        },
                    },
                    'alternative_titles': {
                        'type': 'string',
                        'index_name': 'alternative_title',
                        'index_analyzer': 'nGram_analyzer',
                        'search_analyzer': 'whitespace_analyzer',  
                    },
                    'genres': {
                        'type': 'string',
                        'index_name': 'genre',
                    },
                }
            }
        }
    })

    database.es.indices.create('episodes', body={
        'settings': settings,
        'mappings': {
            'episode': {
                'properties' : {
                    'title': {
                        'type': 'string',
                    },
                    'number': { 'type': 'integer' },
                    'air_date': { 'type': 'date' },
                    'description': {
                        "dynamic" : False,
                        'properties' : {
                            'text': { 'type': 'string' },
                            'url': { 'type': 'string' },
                            'title': { 'type': 'string' },
                        },
                    },
                    'season': { 'type': 'integer' },
                    'episode': { 'type': 'integer' },
                    'show_id': { 'type': 'integer' },
                    'runtime': { 'type': 'integer' },
                },
            }
        }
    })

    database.es.indices.create('images', body={
        'settings': settings,
        'mappings': {
            'image': {
                'properties' : {
                    'id': { 'type': 'integer' },
                    'relation_type': { 'type': 'integer' },
                    'relation_id': { 'type': 'integer' },
                    'external_name': { 'type': 'string' },
                    'external_id': { 'type': 'string' },
                    'height': { 'type': 'integer' },
                    'width': { 'type': 'integer' },
                    'hash': { 'type': 'string' },
                    'source_title': { 'type': 'string' },
                    'source_url': { 'type': 'string' },
                    'type': { 'type': 'integer' },
                    'created': { 'type': 'string' },
                },
            }
        }
    })


if __name__ == '__main__':
    create_indices()