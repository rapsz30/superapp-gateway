/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // add field
  collection.fields.addAt(10, new Field({
    "hidden": false,
    "id": "bool3443592685",
    "name": "aktif",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // remove field
  collection.fields.removeById("bool3443592685")

  return app.save(collection)
})
