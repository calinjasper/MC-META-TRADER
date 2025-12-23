/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("063d5x6zjyc91tk")

  collection.createRule = "   @request.auth.id != \"\""

  return dao.saveCollection(collection)
}, (db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("063d5x6zjyc91tk")

  collection.createRule = ""

  return dao.saveCollection(collection)
})
