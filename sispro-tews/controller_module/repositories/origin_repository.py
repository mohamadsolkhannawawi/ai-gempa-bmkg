
from bson.objectid import ObjectId
from datetime import datetime
from dateutil import parser

def origin_find_by_id_repository(db, origin_id):
    origin_collection = db['origin']

    # ID event yang ingin dicari
    origin_id = ObjectId(origin_id)  
    # Pipeline agregasi
    # pipeline = [
    #     {
    #         '$match': {
    #             '_id': origin_id
    #         }
    #     },
    #    {
    #         '$lookup': {
    #             'from': 'arrival',
    #             'localField': 'arrival_ids',
    #             'foreignField': '_id',
    #             'as': 'arrivals'
    #         }
    #     },
      
    #     {
    #         '$lookup': {
    #             'from': 'magnitude',
    #             'localField': 'magnitude_ids',
    #             'foreignField': '_id',
    #             'as': 'magnitudes'
    #         }
    #     }
       
    # ]
    
    pipeline = [
        {
            '$match': {
                '_id': origin_id
            }
        },
        {
            '$lookup': {
                'from': 'arrival',
                'localField': 'arrival_ids',
                'foreignField': '_id',
                'as': 'arrivals'
            }
        },
        {
            '$lookup': {
                'from': 'magnitude',
                'localField': 'magnitude_ids',
                'foreignField': '_id',
                'as': 'magnitudes'
            }
        },
        {
            '$unwind': {
                'path': '$station_magnitude_ids_per_type',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$lookup': {
                'from': 'station_magnitude',
                'localField': 'station_magnitude_ids_per_type.station_magnitude_ids',
                'foreignField': '_id',
                'as': 'station_magnitude_ids_per_type.station_magnitudes'
            }
        },
        {
            '$unwind': {
                'path': '$station_magnitude_ids_per_type.station_magnitudes',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$lookup': {
                'from': 'station',
                'localField': 'station_magnitude_ids_per_type.station_magnitudes.station_id',
                'foreignField': '_id',
                'as': 'station_magnitude_ids_per_type.station_magnitudes.station_details'
            }
        },
        {
            '$unwind': {
                'path': '$station_magnitude_ids_per_type.station_magnitudes.station',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$group': {
                '_id': {
                    'origin_id': '$_id',
                    'station_magnitude_type': '$station_magnitude_ids_per_type.type'
                },
                'station_magnitudes': {
                    '$push': {
                        '$mergeObjects': [
                            '$station_magnitude_ids_per_type.station_magnitudes',
                            {
                                'station_details': '$station_magnitude_ids_per_type.station_magnitudes.station_details'
                            }
                        ]
                    }
                },
                'doc': {
                    '$first': {
                        'name': '$name',
                        'origin_time': '$origin_time',
                        'arrival_ids': '$arrival_ids',
                        'longitude': '$longitude',
                        'latitude': '$latitude',
                        'depth': '$depth',
                        'region': '$region',
                        'sub_region': '$sub_region',
                        'terrain': '$terrain',
                        'country': '$country',
                        'magnitude_ids': '$magnitude_ids',
                        'modified_by': '$modified_by',
                        'auto_origin_ref_id': '$auto_origin_ref_id',
                        'created_at': '$created_at',
                        'arrivals': '$arrivals',
                        'magnitudes': '$magnitudes'
                    }
                }
            }
        },
        {
            '$group': {
                '_id': '$_id.origin_id',
                'name': {'$first': '$doc.name'},
                'origin_time': {'$first': '$doc.origin_time'},
                'arrival_ids': {'$first': '$doc.arrival_ids'},
                'longitude': {'$first': '$doc.longitude'},
                'latitude': {'$first': '$doc.latitude'},
                'depth': {'$first': '$doc.depth'},
                'region': {'$first': '$doc.region'},
                'sub_region': {'$first': '$doc.sub_region'},
                'terrain': {'$first': '$doc.terrain'},
                'country': {'$first': '$doc.country'},
                'magnitude_ids': {'$first': '$doc.magnitude_ids'},
                'modified_by': {'$first': '$doc.modified_by'},
                'auto_origin_ref_id': {'$first': '$doc.auto_origin_ref_id'},
                'created_at': {'$first': '$doc.created_at'},
                'arrivals': {'$first': '$doc.arrivals'},
                'magnitudes': {'$first': '$doc.magnitudes'},
                'station_magnitude_ids_per_type': {
                    '$push': {
                        'type': '$_id.station_magnitude_type',
                        'station_magnitudes': '$station_magnitudes'
                    }
                }
            }
        }
    ]


    # Menjalankan pipeline agregasi
    try:
        event = list(origin_collection.aggregate(pipeline))
        

        # Menampilkan hasil
        return event
    except TypeError as e:
        print(f"An error occurred: {e}")
