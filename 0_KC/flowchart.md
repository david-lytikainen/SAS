## Admin Flow

```mermaid
flowchart TB
  SU([Start: Sign Up])
  SU1["No public sign-up route exists"]
  SU2["Admin account must already exist"]

  SI([Start: Sign In])
  SI1["Open /admin or /admin/sign-in"]
  SI2["Show admin email and password form"]
  SI3["POST /auth/login"]
  SI4["Invalid login shows error"]
  SI5["Valid login stores JWT"]
  SI6["Open /admin/profile"]
  SI7["Direct /admin/profile also tries stored token"]
  SI8["Invalid token returns to sign-in"]
  SI9["Valid token stays on profile"]

  P0["Profile shows read-only summary"]
  P1["Admin tools accordion: create gallery item"]
  P2["Create item with title, description, optional price, up to 5 images"]
  P3["Crop selected images locally before save"]
  P4["Save uploads images to S3 and saves item"]

  E0["Edit Gallery accordion"]
  E1["Edit title, description, price, publish state, and images"]
  E2["Reorder gallery cards by drag and drop"]
  E3["Reorder images inside one item"]
  E4["Delete item needs confirm click"]
  E5["Sold gallery cards show Sold badge"]

  C0["Services accordion"]
  C1["Create service"]
  C2["Rename service"]
  C3["Archive or unarchive service"]

  O0["All Orders accordion"]
  O1["GET paginated admin order list"]
  O2["Rows include commission, gallery order, and gallery inquiry"]
  O3["Open shared /order/{6_digit} page"]
  O4["Admin can save quote or decline commission"]
  O5["Admin can manually mark accepted"]
  O6["Admin can mark in_progress, shipped, delivered"]
  O7["Admin can add, edit, delete comments"]
  O8["Status changes send customer email"]
  O9["Logout clears token and returns home"]

  SU --> SU1 --> SU2
  SI --> SI1 --> SI2 --> SI3
  SI3 --> SI4
  SI3 --> SI5 --> SI6 --> P0
  SI --> SI7
  SI7 --> SI8
  SI7 --> SI9 --> P0

  P0 --> P1 --> P2 --> P3 --> P4
  P0 --> E0 --> E1 --> E2 --> E3 --> E4 --> E5
  P0 --> C0 --> C1 --> C2 --> C3
  P0 --> O0 --> O1 --> O2 --> O3 --> O4 --> O5 --> O6 --> O7 --> O8 --> O9
```

## Commission Flow

```mermaid
flowchart TB
  SU([Start: Sign Up])
  SU1["No customer sign-up route exists"]
  SU2["Continue as public visitor"]

  SI([Start: Sign In])
  SI1["No customer sign-in route exists"]
  SI2["Returning customer uses direct /order/{6_digit} link"]

  H0["Open home page /"]
  H1["Tap Request a commission"]
  F0["Load active services plus Custom"]
  F1["Fill required name, email, phone, service, instructions, medium, size"]
  F2["Attach up to 5 image files"]
  F3["POST /commissions"]
  F4["Open shared /order/{6_digit} page"]
  F5["Mail setup may also send order link email"]

  O0["Shared order page shows status, service, details, files, comments"]
  O1["Customer can add, edit, delete text comments"]
  O2["New comment appears immediately"]
  O3["Comment later shows email sent or email error"]

  Q0["If status is quoted"]
  Q1["Customer can decline quote"]
  Q2["Customer can pay full quote in Stripe Checkout"]
  Q3["Unused 10% review reward auto-applies by email match"]
  Q4["Return URL or Stripe webhook confirms payment"]
  Q5["Order becomes accepted after payment"]

  D0["Admin later moves order to in_progress, shipped, delivered"]
  D1["Delivered order can be customer-confirmed"]
  D2["Delivered order can show Leave a review"]
  D3["Review requires stars and text"]
  D4["First qualifying review earns one-time 10% reward"]

  SU --> SU1 --> SU2 --> H0
  SI --> SI1 --> SI2 --> O0

  H0 --> H1 --> F0 --> F1 --> F2 --> F3 --> F4 --> F5
  F4 --> O0 --> O1 --> O2 --> O3
  O0 --> Q0
  Q0 --> Q1
  Q0 --> Q2 --> Q3 --> Q4 --> Q5 --> D0 --> D1 --> D2 --> D3 --> D4
```

## Gallery Flow

```mermaid
flowchart TB
  SU([Start: Sign Up])
  SU1["No customer sign-up route exists"]
  SU2["Continue as public visitor"]

  SI([Start: Sign In])
  SI1["Admin can sign in at /admin"]
  SI2["Customer sign-in route does not exist"]
  SI3["Returning customer uses direct /order/{6_digit} link"]

  A0["Admin profile manages gallery items"]
  A1["Create, edit, delete, reorder items and images"]

  H0["Open home page / or /gallery"]
  H1["Browse preview cards or full gallery"]
  H2["Open /gallery/{item_id}"]
  H3["Detail page shows main image, preview squares, cursor-follow zoom"]
  H4["View-only artwork has no buy or question panel"]

  P0["Priced artwork shows Buy and Ask a question"]
  P1["Ask a question requires email and message"]
  P2["POST /gallery/{item_id}/inquiries"]
  P3["Open inquiry at /order/{6_digit}"]
  P4["Inquiry page shows artwork preview, comments, and Buy artwork button"]

  B0["Direct Buy from card or detail page"]
  B1["POST /gallery/{item_id}/checkout"]
  B2["Stripe Checkout collects shipping"]
  B3["Unused 10% review reward auto-applies by email match"]
  B4["Stripe line item name shows reward applied when used"]
  B5["Successful checkout opens paid gallery /order/{6_digit}"]

  O0["Paid gallery order shows artwork, shipping, comments, status"]
  O1["Payment-processing page auto-refreshes until paid"]
  O2["Customer can add, edit, delete comments"]
  O3["Delivered order can be customer-confirmed"]
  O4["Delivered order can accept review"]
  O5["Purchased artwork price is cleared and item becomes view-only"]

  SU --> SU1 --> SU2 --> H0
  SI --> SI1 --> A0 --> A1
  SI --> SI2 --> SI3 --> P3

  H0 --> H1 --> H2 --> H3
  H3 --> H4
  H3 --> P0 --> P1 --> P2 --> P3 --> P4
  P0 --> B0 --> B1 --> B2 --> B3 --> B4 --> B5 --> O0 --> O1 --> O2 --> O3 --> O4 --> O5
  P4 --> B2
```
