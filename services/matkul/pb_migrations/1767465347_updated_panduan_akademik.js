/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "true = true\n\n\n",
    "viewRule": ""
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "status = \"Menunggu Verifikasi\"\n\n",
    "viewRule": "status = \"Terverifikasi\"\n"
  }, collection)

  return app.save(collection)
})
