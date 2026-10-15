/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_666766588")

  // update collection data
  unmarshal({
    "listRule": "true=true",
    "viewRule": "true=true"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_666766588")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.id != \"\"\n",
    "viewRule": "@request.auth.id != \"\"\n"
  }, collection)

  return app.save(collection)
})
