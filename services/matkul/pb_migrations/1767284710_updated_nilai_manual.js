/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_4250196338")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_MZKIEWtxw3` ON `nilai_manual` (`nama_kegiatan`)"
    ]
  }, collection)

  // remove field
  collection.fields.removeById("relation710589754")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_4250196338")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_MZKIEWtxw3` ON `nilai_manual` (\n  `unggah_khs`,\n  `nama_kegiatan`\n)"
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
