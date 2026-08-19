## App Flow

```mermaid
flowchart TB
  subgraph StartSignup[Start 1: Sign Up]
    SU0([Sign Up])
    SU1{What exists in code?}
    SU2[No sign-up route]
    SU3[No sign-up UI]
    SU4[Stay public]
    SU5[Submit commission form]
    SU6[Open shared order link]
    SU7[No in-app admin creation path]
  end

  SU0 --> SU1
  SU1 --> SU2 --> SU3 --> SU4
  SU4 --> SU5 --> SU6
  SU1 --> SU7

  subgraph StartSignin[Start 2: Sign In]
    SI0([Sign In])
    SI1{What exists in code?}
    SI2[Visit /admin or /admin/sign-in]
    SI3[Visit /admin/profile directly]
    SI4[Stored token found]
    SI5[Show Admin Sign In]
    SI6[POST /auth/login]
    SI7[GET /auth/validate-token]
    SI8[Bad login]
    SI9[Token valid]
    SI10[Token invalid]
    SI11[Store JWT in localStorage]
    SI12[Open admin profile]
    SI13[No customer sign-in flow]
    SI14[Customers use /order/123456 directly]
    SI15[Admin session restored while on order page]
  end

  SI0 --> SI1
  SI1 --> SI2 --> SI5 --> SI6
  SI1 --> SI3 --> SI5
  SI1 --> SI4 --> SI7
  SI1 --> SI13 --> SI14
  SI6 -->|401| SI8
  SI6 -->|200| SI11 --> SI12
  SI7 -->|200 on admin route| SI12
  SI7 -->|200 on order route| SI15
  SI7 -->|401 on admin route| SI10 --> SI5
  SI7 -->|401 on order route| SI14

  subgraph PublicVisitor[User Type: Public Visitor]
    PV0[Home at /]
    PV1[Sticky nav: brand, Gallery, Commission]
    PV2[Hero CTAs: Request a commission, View gallery]
    PV3[Gallery preview loads]
    PV4[GET /gallery]
    PV5[Show loading, error, empty, or items]
    PV6[Preview mode: 1 card mobile, 3 cards tablet+]
    PV7[Auto-rotate preview every 5 seconds when needed]
    PV8[Click View Full Gallery]
    PV9[Open /gallery full page]
    PV10[Ask a question on priced artwork]
    PV11[POST /gallery/{item_id}/inquiries]
    PV12[Open gallery inquiry order page]
    PV13[Buy priced artwork]
    PV14[POST /gallery/{item_id}/checkout]
    PV15[Redirect to Stripe Checkout]
    PV16[Commission form loads services]
    PV17[GET /commission-categories]
    PV18[Show active services plus Custom]
    PV19[Fill required fields]
    PV20[Name, email, phone, service, instructions, medium, size]
    PV21[Optional: up to 5 image files]
    PV22[Only image files; client keeps first 5]
    PV23[POST /commissions]
    PV24[Show form error]
    PV25[Server may email order link]
    PV26[Open new commission order page]
  end

  PV0 --> PV1 --> PV2
  PV1 --> PV3 --> PV4 --> PV5 --> PV6 --> PV7
  PV5 --> PV8 --> PV9
  PV5 --> PV10 --> PV11 --> PV12
  PV5 --> PV13 --> PV14 --> PV15
  PV1 --> PV16 --> PV17
  PV17 -->|success| PV18 --> PV19 --> PV20 --> PV21 --> PV22 --> PV23
  PV17 -->|error| PV24
  PV23 -->|400 or 500| PV24
  PV23 -->|200| PV25 --> PV26

  subgraph AnonymousOrderUser[User Type: Anonymous Order-Link User]
    OV0[Open /order/123456]
    OV1[GET /orders/{order_number} without auth]
    OV2{Order kind found}
    OV3[Commission order page]
    OV4[Gallery inquiry page]
    OV5[Paid gallery order page]
    OV6[404 or load error]
    OV7[Shared page shows Back home, details, files, comments]
    OV8{checkout_session_id in URL?}
    OV9[POST /orders/{order_number}/confirm-payment]
    OV10[Show payment confirmed and remove query string]
    OV11[Show confirm-payment error]
    OV12{Commission status is quoted?}
    OV13[Decline quote]
    OV14[POST /orders/{order_number}/decline]
    OV15[Pay quote]
    OV16[POST /orders/{order_number}/checkout]
    OV17[Redirect to Stripe Checkout]
    OV18{Gallery inquiry has price?}
    OV19[Buy artwork from inquiry]
    OV20[POST /gallery-inquiries/{order_number}/checkout]
    OV21{Paid gallery order still processing?}
    OV22[Auto-refresh every 3 seconds]
    OV23{Delivered and not yet confirmed?}
    OV24[Confirm received prompt]
    OV25[POST /orders/{order_number}/confirm-received]
    OV26[Show receipt confirmation error]
    OV27[Add customer comment]
    OV28[PATCH own customer comment]
    OV29[DELETE own customer comment]
    OV30[Show comment action error]
    OV31[Stripe webhook may also complete payment server-side]
  end

  OV0 --> OV1 --> OV2
  OV2 -->|commission| OV3 --> OV7
  OV2 -->|gallery_inquiry| OV4 --> OV7
  OV2 -->|gallery| OV5 --> OV7
  OV2 -->|missing| OV6
  OV7 --> OV8
  OV8 -->|yes| OV9
  OV9 -->|paid + matching session| OV10
  OV9 -->|bad session or unpaid| OV11
  OV8 -->|no| OV12
  OV12 -->|commission + quoted| OV13 --> OV14
  OV12 -->|commission + quoted| OV15 --> OV16 --> OV17
  OV12 -->|gallery inquiry| OV18
  OV18 -->|priced| OV19 --> OV20 --> OV17
  OV18 -->|not priced| OV27
  OV12 -->|other order state| OV27
  OV5 --> OV21
  OV21 -->|yes| OV22
  OV5 --> OV23
  OV3 --> OV23
  OV23 -->|yes| OV24 --> OV25
  OV25 -->|error| OV26
  OV7 --> OV27
  OV7 --> OV28
  OV7 --> OV29
  OV27 -->|error| OV30
  OV28 -->|error| OV30
  OV29 -->|error| OV30
  OV17 --> OV31

  subgraph SignedInAdmin[User Type: Signed-In Admin]
    AD0[Open /admin/profile]
    AD1[Profile route requires token]
    AD2[Read-only profile summary]
    AD3[Name, email, role]
    AD4[Admin Tools heading]
    AD5[Create Gallery Item accordion]
    AD6[Pick local image]
    AD7[Local preview only]
    AD8[Enter title, description, optional price]
    AD9[POST /admin/gallery]
    AD10[PATCH /admin/gallery/{item_id}]
    AD11[Show gallery success or error]
    AD12[Existing Gallery accordion]
    AD13[GET /admin/gallery]
    AD14[Responsive edit grid]
    AD15[2 columns mobile, 3 tablet, 5 desktop]
    AD16[Drag to reorder]
    AD17[POST /admin/gallery/reorder]
    AD18[Edit existing item]
    AD19[Two-step delete]
    AD20[DELETE /admin/gallery/{item_id}]
    AD21[Services accordion]
    AD22[GET /admin/commission-categories]
    AD23[Create service]
    AD24[PATCH service name]
    AD25[Archive or restore service]
    AD26[All Orders accordion]
    AD27[GET /admin/orders?page=n&page_size=10]
    AD28[Previous / Next pagination]
    AD29[Open shared order page]
    AD30[Logout]
  end

  AD0 --> AD1 --> AD2 --> AD3 --> AD4
  AD4 --> AD5 --> AD6 --> AD7 --> AD8
  AD8 -->|new item| AD9 --> AD11
  AD8 -->|editing current item| AD10 --> AD11
  AD4 --> AD12 --> AD13 --> AD14 --> AD15
  AD14 --> AD16 --> AD17 --> AD11
  AD14 --> AD18 --> AD5
  AD14 --> AD19 --> AD20 --> AD11
  AD4 --> AD21 --> AD22
  AD22 --> AD23
  AD22 --> AD24
  AD22 --> AD25
  AD0 --> AD26 --> AD27 --> AD28 --> AD29
  AD0 --> AD30

  subgraph AdminOnOrderPage[User Type: Signed-In Admin On Shared Order Page]
    AO0[GET /orders/{order_number} with Bearer token]
    AO1[viewerIsAdmin becomes true]
    AO2[Show admin controls]
    AO3{Commission order?}
    AO4[Save quote]
    AO5[POST /admin/orders/{order_number}/quote]
    AO6[Decline order]
    AO7[POST /admin/orders/{order_number}/decline]
    AO8[Mark accepted]
    AO9[POST /admin/orders/{order_number}/status accepted]
    AO10[Accepted blocked until quote exists]
    AO11[Mark in progress]
    AO12[Mark shipped]
    AO13[Mark delivered]
    AO14[POST /admin/orders/{order_number}/status in_progress]
    AO15[POST /admin/orders/{order_number}/status shipped]
    AO16[POST /admin/orders/{order_number}/status delivered]
    AO17[Add admin comment]
    AO18[PATCH own admin comment]
    AO19[DELETE own admin comment]
    AO20[Show admin action error or success]
  end

  AO0 --> AO1 --> AO2 --> AO3
  AO3 -->|commission| AO4 --> AO5 --> AO20
  AO3 -->|commission| AO6 --> AO7 --> AO20
  AO3 -->|commission| AO8 --> AO9
  AO9 -->|missing quote| AO10
  AO9 -->|ok| AO20
  AO3 -->|commission or paid gallery| AO11 --> AO14 --> AO20
  AO3 -->|commission or paid gallery| AO12 --> AO15 --> AO20
  AO3 -->|commission or paid gallery| AO13 --> AO16 --> AO20
  AO2 --> AO17 --> AO20
  AO2 --> AO18 --> AO20
  AO2 --> AO19 --> AO20

  SU4 --> PV0
  SU6 --> OV0
  SI8 --> SI5
  SI9 --> SI12
  SI12 --> AD0
  SI14 --> OV0
  SI15 --> AO0
  PV12 --> OV0
  PV26 --> OV0
  AD29 --> AO0
```
