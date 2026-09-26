



def get_auto_gempa_repo(db):
  
    event_data = db.event.aggregate([
        {
            "$lookup": {
                "from": "origin",
                "localField": "preferred_origin_id",
                "foreignField": "_id",
                "as": "origin_data"
            }
        },
        {
            "$unwind": "$origin_data"
        },
        {
            "$sort": {
                "origin_data.origin_time": -1
            }
        },
        {
            "$limit": 1
        }
    ])
    event_data = list(event_data)[0]

    if event_data:
        # Join dengan magnitude collection berdasarkan magnitude_ids
        magnitude_collection = db["magnitude"]
        magnitudes = list(magnitude_collection.find({
            "_id": {"$in": event_data["origin_data"]["magnitude_ids"]},
            "type": "MLv"
        }))

        # Jika tidak ada hasil, ambil semua magnitudes tanpa filter "MLv"
        if not magnitudes:
            magnitudes = list(magnitude_collection.find({
                "_id": {"$in": event_data["origin_data"]["magnitude_ids"]}
            }))
        event_data["origin_data"]["magnitudes"] = magnitudes

        arrival_collection = db["arrival"]
        arrivals = list(arrival_collection.find({"_id": {"$in": event_data["origin_data"]["arrival_ids"]}}))

        # Join setiap arrival dengan station collection berdasarkan station_id
        station_collection = db["station"]
        for arrival in arrivals:
            station = station_collection.find_one({"_id": arrival["station_id"]})
            arrival["station"] = station

        # Tambahkan arrivals yang telah dijoin ke dalam origin_data
        event_data["origin_data"]["arrivals"] = arrivals

   
    return event_data