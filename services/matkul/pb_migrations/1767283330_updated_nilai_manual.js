/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_4250196338")

  // update collection data
  unmarshal({
    "createRule": "true=true\n\n",
    "deleteRule": "session_key = @request.query.session_key\n\n",
    "indexes": [
      "CREATE UNIQUE INDEX `idx_MZKIEWtxw3` ON `nilai_manual` (\n  `unggah_khs`,\n  `nama_kegiatan`\n)"
    ],
    "listRule": "session_key = @request.query.session_key\n\n",
    "updateRule": "session_key = @request.query.session_key\n",
    "viewRule": "session_key = @request.query.session_key\n\n"
  }, collection)

  // remove field
  collection.fields.removeById("relation1007721002")

  // remove field
  collection.fields.removeById("select2063623452")

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

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_4250196338")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.id != \"\"\n\n",
    "deleteRule": "@request.auth.id != \"\" && pengguna.id = @request.auth.id\n\n",
    "indexes": [
      "CREATE UNIQUE INDEX `idx_MZKIEWtxw3` ON `nilai_manual` (\n  `unggah_khs`,\n  `nama_kegiatan`,\n  `pengguna`\n)"
    ],
    "listRule": "@request.auth.id != \"\" && pengguna.id = @request.auth.id\n\n",
    "updateRule": "@request.auth.id != \"\" && pengguna.id = @request.auth.id\n",
    "viewRule": "@request.auth.id != \"\" && pengguna.id = @request.auth.id\n\n"
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
      "Lulus",
      "Tidak Lulus"
    ]
  }))

  // remove field
  collection.fields.removeById("text4148769683")

  return app.save(collection)
})
