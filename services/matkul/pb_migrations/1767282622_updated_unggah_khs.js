/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3572141482")

  // update collection data
  unmarshal({
    "listRule": "session_key = @request.query.session_key\n",
    "updateRule": "session_key = @request.query.session_key\n",
    "viewRule": "session_key = @request.query.session_key\n"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3572141482")

  // update collection data
  unmarshal({
    "listRule": "",
    "updateRule": "",
    "viewRule": ""
  }, collection)

  return app.save(collection)
})
