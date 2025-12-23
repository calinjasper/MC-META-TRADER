/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("536e0h3a616qojd")

  // add
  collection.schema.addField(new SchemaField({
    "system": false,
    "id": "bpldcfcj",
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
  const collection = dao.findCollectionByNameOrId("536e0h3a616qojd")

  // remove
  collection.schema.removeField("bpldcfcj")

  return dao.saveCollection(collection)
})
