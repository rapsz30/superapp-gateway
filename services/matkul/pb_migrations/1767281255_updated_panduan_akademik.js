/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "",
    "viewRule": ""
  }, collection)

  // remove field
  collection.fields.removeById("bool3443592685")

  // add field
  collection.fields.addAt(6, new Field({
    "hidden": false,
    "id": "select2063623452",
    "maxSelect": 1,
    "name": "status",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "Menunggu Verifikasi",
      "Terverifikasi",
      "Ditolak",
      "Diarsipkan"
    ]
  }))

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

  // add field
  collection.fields.addAt(9, new Field({
    "hidden": false,
    "id": "date894078913",
    "max": "",
    "min": "",
    "name": "verified_at",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "date"
  }))

  // add field
  collection.fields.addAt(10, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text2786581319",
    "max": 0,
    "min": 0,
    "name": "catatan_admin",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(11, new Field({
    "hidden": false,
    "id": "select1602912115",
    "maxSelect": 1,
    "name": "source",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "admin",
      "user"
    ]
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "aktif = true",
    "viewRule": "aktif = true"
  }, collection)

  // add field
  collection.fields.addAt(6, new Field({
    "hidden": false,
    "id": "bool3443592685",
    "name": "aktif",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  // remove field
  collection.fields.removeById("select2063623452")

  // remove field
  collection.fields.removeById("relation3823579430")

  // remove field
  collection.fields.removeById("relation1624678591")

  // remove field
  collection.fields.removeById("date894078913")

  // remove field
  collection.fields.removeById("text2786581319")

  // remove field
  collection.fields.removeById("select1602912115")

  return app.save(collection)
})
