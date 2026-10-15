/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3572141482");

  return app.delete(collection);
}, (app) => {
  const collection = new Collection({
    "createRule": "",
    "deleteRule": "",
    "fields": [
      {
        "autogeneratePattern": "[a-z0-9]{15}",
        "hidden": false,
        "id": "text3208210256",
        "max": 15,
        "min": 15,
        "name": "id",
        "pattern": "^[a-z0-9]+$",
        "presentable": false,
        "primaryKey": true,
        "required": true,
        "system": true,
        "type": "text"
      },
      {
        "hidden": false,
        "id": "file4037587555",
        "maxSelect": 1,
        "maxSize": 0,
        "mimeTypes": [
          "application/pdf"
        ],
        "name": "file_khs",
        "presentable": false,
        "protected": false,
        "required": true,
        "system": false,
        "thumbs": [],
        "type": "file"
      },
      {
        "hidden": false,
        "id": "select2063623452",
        "maxSelect": 1,
        "name": "status",
        "presentable": false,
        "required": false,
        "system": false,
        "type": "select",
        "values": [
          "diunggah",
          "diproses",
          "diparsing",
          "selesai",
          "gagal"
        ]
      },
      {
        "cascadeDelete": false,
        "collectionId": "pbc_666766588",
        "hidden": false,
        "id": "relation3069014806",
        "maxSelect": 1,
        "minSelect": 0,
        "name": "jurusan",
        "presentable": false,
        "required": true,
        "system": false,
        "type": "relation"
      },
      {
        "hidden": false,
        "id": "json2355997912",
        "maxSize": 0,
        "name": "parsed_rows",
        "presentable": false,
        "required": false,
        "system": false,
        "type": "json"
      },
      {
        "convertURLs": false,
        "hidden": false,
        "id": "editor3851093059",
        "maxSize": 0,
        "name": "teks_ekstraksi",
        "presentable": false,
        "required": false,
        "system": false,
        "type": "editor"
      },
      {
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
      },
      {
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
      }
    ],
    "id": "pbc_3572141482",
    "indexes": [],
    "listRule": "session_key = @request.query.session_key\n",
    "name": "unggah_khs",
    "system": false,
    "type": "base",
    "updateRule": "session_key = @request.query.session_key\n",
    "viewRule": "session_key = @request.query.session_key\n"
  });

  return app.save(collection);
})
