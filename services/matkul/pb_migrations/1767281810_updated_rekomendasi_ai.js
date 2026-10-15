/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "listRule": "",
    "viewRule": ""
  }, collection)

  // remove field
  collection.fields.removeById("relation1007721002")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "listRule": "pengguna = @request.auth.id\n",
    "viewRule": "pengguna = @request.auth.id\n"
  }, collection)

  // add field
  collection.fields.addAt(1, new Field({
    "cascadeDelete": false,
    "collectionId": "_pb_users_auth_",
    "hidden": false,
    "id": "relation1007721002",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "pengguna",
    "presentable": false,
    "required": true,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
})
