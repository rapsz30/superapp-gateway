/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "indexes": []
  }, collection)

  // remove field
  collection.fields.removeById("relation710589754")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_nfelhK6FMR` ON `rekomendasi_ai` (`unggah_khs`)"
    ]
  }, collection)

  // add field
  collection.fields.addAt(1, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_3572141482",
    "hidden": false,
    "id": "relation710589754",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "unggah_khs",
    "presentable": false,
    "required": true,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
})
