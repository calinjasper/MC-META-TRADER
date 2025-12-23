/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("536e0h3a616qojd")

  collection.createRule = ""

  return dao.saveCollection(collection)
}, (db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("536e0h3a616qojd")

  collection.createRule = "   @request.auth.id != \"\""

  return dao.saveCollection(collection)
})
