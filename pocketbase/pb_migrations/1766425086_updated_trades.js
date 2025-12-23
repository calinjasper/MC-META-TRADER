/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("zo5ilz28ovqv8my")

  collection.createRule = ""

  return dao.saveCollection(collection)
}, (db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("zo5ilz28ovqv8my")

  collection.createRule = "   @request.auth.id != \"\""

  return dao.saveCollection(collection)
})
