# API Flow Test

## Test Query
Laptop under ₹50,000 with Best Review

---

# INTENT API

URL:
https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent

Method:
POST

Parameters:
None

Request:
```json
{
  "user_message": "Laptop under \u20b950,000 with Best Review",
  "history": []
}
```

Response:
```json
{
  "intent": "recommendation",
  "entity": "laptop",
  "query_text": "Laptop under \u20b950,000 with Best Review",
  "keywords": "****************",
  "budget": 50000.0,
  "priority": "review",
  "count": 5,
  "brand": null,
  "compare_items": [],
  "needs_summary": true,
  "in_scope": true,
  "rejection_reason": null
}
```

---

# REVIEW API

URL:
Not Called

Parameters:
N/A

Request:
N/A

Response:
Skipped or Not Triggered by Query Intent

---

# PRODUCT API

URL:
https://pricee.com/api/v2/productList.php

Method:
GET

Parameters:
```json
{
  "entity": "laptop",
  "budget": 50000.0,
  "priority": "review",
  "brand": null,
  "count": 5,
  "keywords": "****************",
  "query_text": "Laptop under \u20b950,000 with Best Review"
}
```

Request:
None

Response:
```json
[
  {
    "id": "2-b09n7lwqrq",
    "name": "ULTRAZONE Laptop Internal Speaker Compatible for Lenovo 320-14AST Laptop (ideapad), 320-14IAP Laptop (ideapad), 320-14IKB Laptop (ideapad) 320-14ISK Laptop (ideapad)",
    "brand": "ultrazone",
    "entity": "laptop",
    "category": "laptops",
    "price": 799.0,
    "currency": "INR",
    "rating": 50.0,
    "image_url": "https://m.media-amazon.com/images/I/21FQZ3w hwL._SL160_.jpg",
    "url": "https://pricee.com/api/redirect/t.php?itemid=2-b09n7lwqrq&pos=0",
    "review_url": null,
    "discount": "72",
    "availability": "In Stock",
    "store_name": "amazon",
    "key_specs": "****************"
  },
  {
    "id": "252-3000104738829",
    "name": "Laptop",
    "brand": "silver",
    "entity": "laptop",
    "category": "laptops",
    "price": 45000.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://sellerconnect.vikrra.in/api/v1/images/itemImage/prodnirmitbapondcorg/cdddfc926879290877dc5a07bf29fed394e76ca1c560824ced13c50589aaf1f397e3c9d58014b8a3e272b6df4d167d01/image.png",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-3000104738829&pos=1",
    "review_url": null,
    "discount": "22",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-1169616831",
    "name": "laptop bag",
    "brand": "nr boutique",
    "entity": "laptop",
    "category": "laptops",
    "price": 289.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdnaz.plotch.io/image/upload/C/V/PLOvsRTzd11746856251_fc1f09d1cbad2aeabb7b1bdb4d978cff009db5246b8f7752edc5270afa0c072a.png",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-1169616831&pos=2",
    "review_url": null,
    "discount": "3",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-1169426011",
    "name": "laptop bag",
    "brand": "pooja boutique",
    "entity": "laptop",
    "category": "laptops",
    "price": 289.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdnaz.plotch.io/image/upload/C/V/PLOibWFBsL1746749849_194ea31f21043a214fbd22e9ee3fe7b7b7292532ec0314fb87b244f1c291a679.png",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-1169426011&pos=3",
    "review_url": null,
    "discount": "3",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-1169426012",
    "name": "laptop bag",
    "brand": "pooja boutique",
    "entity": "laptop",
    "category": "laptops",
    "price": 289.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdnaz.plotch.io/image/upload/C/V/PLOKpJvRTL1746749846_023c0fd4d628ff9933b7c46852df05b5b8b575fc5e867389ff5e2614b80737d0.png",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-1169426012&pos=4",
    "review_url": null,
    "discount": "3",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-271196",
    "name": "Personalised Laptop Stand | Buy Custom Portable Laptop Stand Online",
    "brand": "vedant security solution",
    "entity": "laptop",
    "category": "laptops",
    "price": 500.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://prodondcdoc.easypay.co.in/ondc_seller_product/EP_SELLER_KQUUQN7PGQ/EP_SELLER_KQUUQN7PGQ_IMG_1765383906132.jpg",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-271196&pos=5",
    "review_url": null,
    "discount": "",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42644007",
    "name": "Alpha Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/products/2_f33ddfc7-fb95-43e8-8c18-f26571c83fee.jpg?v=1616521717",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42644007&pos=6",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42662526",
    "name": "Canvas Painting Laptop Sleeve Canvas Painting Laptop Sleeve - Canvas Painting 2",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/products/16.jpg?v=1616521670",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42662526&pos=7",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42669060",
    "name": "Embrave Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/files/592.jpg?v=1723285019",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42669060&pos=8",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42894940",
    "name": "Chicago Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/files/614.jpg?v=1723725934",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42894940&pos=9",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42662525",
    "name": "Canvas Painting Laptop Sleeve Canvas Painting Laptop Sleeve - Canvas Painting 1",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/products/16.jpg?v=1616521670",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42662525&pos=10",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42666091",
    "name": "Manila Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/products/71_55969f0b-ab96-4632-a0ab-da31822a7bb5.jpg?v=1616521668",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42666091&pos=11",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42664563",
    "name": "Lama Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/files/572.jpg?v=1719687765",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42664563&pos=12",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42668763",
    "name": "Shiva Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/products/126_cf622b8f-0f16-439b-8d78-8ff35d90625a.jpg?v=1616521673",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42668763&pos=13",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  },
  {
    "id": "252-42664008",
    "name": "Mediate Laptop Sleeve",
    "brand": "wrapcart",
    "entity": "laptop",
    "category": "laptops",
    "price": 458.0,
    "currency": "INR",
    "rating": 0.0,
    "image_url": "https://cdn.shopify.com/s/files/1/0534/7849/0267/files/574.jpg?v=1719687751",
    "url": "https://pricee.com/api/redirect/t.php?itemid=252-42664008&pos=14",
    "review_url": null,
    "discount": "49",
    "availability": "In Stock",
    "store_name": "digihaat",
    "key_specs": "****************"
  }
]
```

---

# SEARCH API

URL:
Not Called

Parameters:
N/A

Request:
N/A

Response:
Skipped or Not Triggered by Query Intent

---

# OUTPUT API

URL:
https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent

Method:
POST

Parameters:
None

Request:
```json
{
  "user_message": "Laptop under \u20b950,000 with Best Review",
  "parsed_query": {
    "intent": "recommendation",
    "entity": "laptop",
    "query_text": "Laptop under \u20b950,000 with Best Review",
    "keywords": "****************",
    "budget": 50000.0,
    "priority": "review",
    "count": 5,
    "brand": null,
    "compare_items": [],
    "needs_summary": true,
    "in_scope": true,
    "rejection_reason": null
  },
  "context_data": {
    "products_context": "Laptop\n\u20b945,000\nRating 0\n22 off\nIn Stock\n\nULTRAZONE Laptop Internal Speaker Compatible for Lenovo 320-14AST Laptop (ideapad), 320-14IAP Laptop (ideapad), 320-14IKB Laptop (ideapad) 320-14ISK Laptop (ideapad)\n\u20b9799\nRating 50\n72 off\nIn Stock\n\nLama Laptop Sleeve\n\u20b9458\nRating 0\n49 off\nIn Stock\n\nAlpha Laptop Sleeve\n\u20b9458\nRating 0\n49 off\nIn Stock\n\nShiva Laptop Sleeve\n\u20b9458\nRating 0\n49 off\nIn Stock"
  }
}
```

Response:
```json
{
  "generated_summary": "Based on the information available, we do not have a specific laptop model under \u20b950,000 with a high rating or \"best review\" to recommend at this time. The generic \"Laptop\" entry is priced at \u20b945,000 but has a rating of 0. Other items listed are laptop accessories or parts, not full laptops."
}
```

---
