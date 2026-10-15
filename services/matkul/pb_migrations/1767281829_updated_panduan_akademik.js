/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // remove field
  collection.fields.removeById("relation3823579430")

  // remove field
  collection.fields.removeById("relation1624678591")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // add field
  collection.fields.addAt(7, new Field({
    "cascadeDelete": false,
    "collectionId": "_pb_users_auth_",
    "hidden": false,
    "id": "relation3823579430",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "uploaded_by",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  // add field
  collection.fields.addAt(8, new Field({
    "cascadeDelete": false,
    "collectionId": "_pb_users_auth_",
    "hidden": false,
    "id": "relation1624678591",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "verified_by",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
})
