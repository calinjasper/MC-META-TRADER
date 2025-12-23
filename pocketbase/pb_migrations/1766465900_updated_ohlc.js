/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("fihcll9ab56tict")

  // add
  collection.schema.addField(new SchemaField({
    "system": false,
    "id": "wy4yfhcj",
    "name": "timestamp_ist",
    "type": "text",
    "required": false,
    "presentable": false,
    "unique": false,
    "options": {
      "min": null,
      "max": null,
      "pattern": ""
    }
  }))

  return dao.saveCollection(collection)
}, (db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("fihcll9ab56tict")

  // remove
  collection.schema.removeField("wy4yfhcj")

  return dao.saveCollection(collection)
})
