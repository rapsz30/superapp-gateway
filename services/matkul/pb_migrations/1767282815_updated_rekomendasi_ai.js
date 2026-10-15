/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "listRule": "session_key = @request.query.session_key\n",
    "updateRule": "session_key = @request.query.session_key\n",
    "viewRule": "session_key = @request.query.session_key\n"
  }, collection)

  // add field
  collection.fields.addAt(6, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text4148769683",
    "max": 0,
    "min": 0,
    "name": "session_key",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(7, new Field({
    "hidden": false,
    "id": "select2063623452",
    "maxSelect": 1,
    "name": "status",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "diproses",
      "selesai",
      "gagal"
    ]
  }))

  // add field
  collection.fields.addAt(8, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text737763667",
    "max": 0,
    "min": 0,
    "name": "error_message",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3901242791")

  // update collection data
  unmarshal({
    "listRule": "",
    "updateRule": null,
    "viewRule": ""
  }, collection)

  // remove field
  collection.fields.removeById("text4148769683")

  // remove field
  collection.fields.removeById("select2063623452")

  // remove field
  collection.fields.removeById("text737763667")

  return app.save(collection)
})
