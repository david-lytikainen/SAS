## Admin Flow

```mermaid
flowchart TB
  SU([Start: Sign Up])
  SU1["No public sign-up route exists"]
  SU2["Admin account must already exist before sign-in"]

  SI([Start: Sign In])
  SI1["Open /admin or /admin/sign-in"]
  SI2["Show admin email and password form"]
  SI3["POST /auth/login"]
  SI4["Invalid login shows error"]
  SI5["Valid login stores JWT and opens /admin/profile"]
  SI6["Direct /admin/profile also tries stored token"]
  SI7["Invalid or expired token returns to sign-in"]
  SI8["Valid token stays on profile"]

  P0["Profile shows read-only name, email, and role"]

  G0["Create Gallery Item accordion"]
  G1["Add title, description, optional price, and up to 5 images"]
  G2["Crop selected images locally before save"]
  G3["Save uploads to S3 and saves gallery item"]

  E0["Existing Gallery accordion"]
  E1["Edit title, description, and optional price"]
  E2["Replace images or reorder saved images"]
  E3["Drag gallery cards to reorder and auto-save"]
  E4["Delete needs confirm click"]
  E5["Sold items show Sold badge"]

  C0["Services accordion"]
  C1["Create service"]
  C2["Rename service"]
  C3["Archive or restore service"]

  O0["All Orders accordion"]
  O1["Load paginated mixed order list"]
  O2["Rows include commission, gallery order, and gallery inquiry"]
  O3["Inquiry rows are labeled and confirmed deliveries show a green checkmark"]
  O4["Open shared /order/{6_digit} page"]
  O5["Admin can add, edit, delete comments"]
  O6["Commission orders can save quote, decline, or mark accepted"]
  O7["Orders can be marked in_progress, shipped, or delivered"]
  O8["Status changes send customer email"]
  O9["Logout clears token and returns home"]

  SU --> SU1 --> SU2
  SI --> SI1 --> SI2 --> SI3
  SI3 --> SI4
  SI3 --> SI5 --> P0
  SI --> SI6
  SI6 --> SI7
  SI6 --> SI8 --> P0

  P0 --> G0 --> G1 --> G2 --> G3
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
  SI2["Returning customer opens direct /order/{6_digit} link"]

  H0["Open home page /"]
  H1["Tap Request a commission"]
  F0["Load active services plus Custom option"]
  F1["Fill required name, email, phone, service, instructions, medium, and size"]
  F2["Attach up to 5 image files"]
  F3["POST /commissions"]
  F4["Open shared /order/{6_digit} page"]
  F5["Mail setup may also send order link email"]

  O0["Shared order page shows status, service, details, files, and comments"]
  O1["Customer can add, edit, and delete text comments"]
  O2["New comment appears immediately"]
  O3["Comment later shows email sent or email error"]

  Q0["If status is quoted"]
  Q1["Customer can decline quote"]
  Q2["Customer can pay full quote in Stripe Checkout"]
  Q3["Unused 10% review reward auto-applies by email match"]
  Q4["Browser return or Stripe webhook confirms payment"]
  Q5["Order becomes accepted after payment"]

  D0["Admin later moves order to in_progress, shipped, and delivered"]
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
  SI1["Admin can sign in at /admin and manage gallery from profile"]
  SI2["Customer sign-in route does not exist"]
  SI3["Returning customer uses direct /order/{6_digit} link"]

  A0["Admin profile can create, edit, delete, crop, and reorder gallery items"]

  H0["Open home page / or full gallery /gallery"]
  H1["Browse gallery cards"]
  H2["Open /gallery/{item_id}"]
  H3["Detail page shows main image, preview squares, and cursor-follow zoom"]
  H4["View-only artwork has no buy or question panel"]

  P0["Priced artwork shows Buy and Ask a question"]
  P1["Question flow requires email and message"]
  P2["POST /gallery/{item_id}/inquiries"]
  P3["Open inquiry at /order/{6_digit}"]
  P4["Inquiry page shows artwork preview, comments, and Buy artwork button"]

  B0["Buy flow requires email"]
  B1["POST /gallery/{item_id}/checkout or /gallery-inquiries/{order_number}/checkout"]
  B2["Stripe Checkout collects shipping"]
  B3["Unused 10% review reward auto-applies by email match"]
  B4["Stripe Checkout also shows reward text when discount is used"]
  B5["Successful checkout opens paid gallery /order/{6_digit}"]

  O0["Paid gallery order shows artwork, shipping, status, and comments"]
  O1["Payment-processing page auto-refreshes until paid"]
  O2["Comments open after payment finishes"]
  O3["Customer can add, edit, and delete comments"]
  O4["Delivered order can be customer-confirmed and reviewed"]
  O5["Purchased artwork price is cleared and item becomes view-only"]

  SU --> SU1 --> SU2 --> H0
  SI --> SI1 --> A0
  SI --> SI2 --> SI3 --> P3

  H0 --> H1 --> H2 --> H3
  H3 --> H4
  H3 --> P0 --> P1 --> P2 --> P3 --> P4
  P0 --> B0 --> B1 --> B2 --> B3 --> B4 --> B5 --> O0 --> O1 --> O2 --> O3 --> O4 --> O5
  P4 --> B1
```
