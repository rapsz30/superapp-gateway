/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "status = \"Terverifikasi\"\n\n"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_139408879")

  // update collection data
  unmarshal({
    "listRule": "true=true\n"
  }, collection)

  return app.save(collection)
})
