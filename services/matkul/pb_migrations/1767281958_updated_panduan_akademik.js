/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "createRule": "true = true\n\n",
    "listRule": "status = \"terverifikasi\"\n",
    "viewRule": "status = \"terverifikasi\"\n"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "createRule": null,
    "listRule": "",
    "viewRule": ""
  }, collection)

  return app.save(collection)
})
