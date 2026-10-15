/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3572141482")

  // update collection data
  unmarshal({
    "createRule": "",
    "deleteRule": "",
    "listRule": "",
    "updateRule": "",
    "viewRule": ""
  }, collection)

  // remove field
  collection.fields.removeById("relation1007721002")

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3572141482")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.id != \"\"\n",
    "deleteRule": "pengguna = @request.auth.id",
    "listRule": "pengguna = @request.auth.id",
    "updateRule": "pengguna = @request.auth.id",
    "viewRule": "pengguna = @request.auth.id"
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
