## App Flow

```mermaid
flowchart TD
  subgraph SignupFlow[Start 1: Sign Up]
    SU0([Sign Up]) --> SU1[Enter first name, last name, email, phone, birthday, gender, church, password, confirm password]
    SU1 --> SU2{Valid form?}
    SU2 -- No --> SU3[Show validation error]
    SU2 -- Yes --> SU4[POST /signup]
    SU4 --> SU5{Unique email and valid gender?}
    SU5 -- No --> SU6[Show API error<br/>duplicate account or invalid input]
    SU5 -- Yes --> SU7[Create attendee account<br/>role_id = 1]
    SU7 --> SU8[Return JWT and auto sign in]
    SU8 --> SU9[Redirect to /events with login splash]
    SU9 --> SU10{Signed-up user path}
    SU10 -->|Stay attendee| ATT0
    SU10 -->|Open Create tab and complete Stripe Connect later| ORG0
  end

  subgraph SigninFlow[Start 2: Sign In]
    SI0([Sign In]) --> SI1[Enter email and password]
    SI1 --> SI2{Credentials valid?}
    SI2 -- No --> SI3[Show login error]
    SI3 --> SI4[Optional Forgot Password]
    SI4 --> SI5[POST /forgot-password]
    SI5 --> SI6[Open reset link]
    SI6 --> SI7[POST /reset-password/:token]
    SI2 -- Yes --> SI8[Return JWT and user]
    SI8 --> SI9[Redirect to /events with login splash]
    SI9 --> SI10{Current role}
    SI10 -->|Attendee| ATT0
    SI10 -->|Organizer| ORG0
    SI10 -->|Admin| ADM0
  end

  subgraph SharedPages[Shared Authenticated Pages]
    SH0[/events route behind PrivateRoute/]
    SH1[/profile route behind PrivateRoute/]
    SH2[Top-right username opens Profile]
    SH1 --> SH3[Read-only profile cards]
    SH3 --> SH4[Edit mode with save and cancel icons]
    SH4 --> SH5[PATCH /profile]
    SH1 --> SH6[Log out from profile card]
  end

  subgraph AttendeePath[Attendee Path]
    ATT0[Events page] --> ATT1{Any checked-in In Progress event?}
    ATT1 -- Yes --> ATT2[Only that single in-progress event stays visible]
    ATT1 -- No --> ATT3[Normal event list]

    ATT2 --> ATT4{Choose tab}
    ATT3 --> ATT4
    ATT4 -->|My| ATT5[See my registered, waitlisted, and created events]
    ATT4 -->|All| ATT6[See all non-mock events]
    ATT4 -->|Create| ATT7[See Stripe organizer setup card]

    ATT7 --> ATT8[Continue to Stripe onboarding]
    ATT8 --> ATT9[Return and refresh organizer status]
    ATT9 --> ORG0

    ATT6 --> ATT10{Open event status}
    ATT10 -->|Registration Open and not registered| ATT11[Tap Sign Up]
    ATT10 -->|In Progress| ATT12[No signup button]
    ATT10 -->|Completed or Past| ATT13[Read-only past event card]

    ATT11 --> ATT14{Paid event?}
    ATT14 -- No --> ATT15[POST /events/:id/register]
    ATT15 --> ATT16{Validation outcome}
    ATT16 -->|Success| ATT17[Registered]
    ATT16 -->|Full or gender cap reached| ATT18[Offer waitlist]
    ATT16 -->|Other error| ATT19[Show API error]

    ATT14 -- Yes --> ATT20[POST /events/:id/checkout]
    ATT20 --> ATT21{Checkout creation outcome}
    ATT21 -->|Success| ATT22[Redirect to Stripe Checkout]
    ATT22 --> ATT23[Stripe webhook checkout.session.completed]
    ATT23 --> ATT24[Webhook calls register_for_event]
    ATT24 --> ATT17
    ATT21 -->|Full or gender cap reached| ATT18
    ATT21 -->|Other error| ATT19

    ATT18 --> ATT25{Join waitlist?}
    ATT25 -- Yes --> ATT26[POST /events/:id/register with join_waitlist=true]
    ATT26 --> ATT27[Waitlisted]
    ATT25 -- No --> ATT28[Stay unregistered]

    ATT5 --> ATT29{My event registration state}
    ATT29 -->|Waitlisted| ATT30[Leave waitlist via cancel-registration]
    ATT29 -->|Registered and not checked in| ATT31[Cancel registration]
    ATT29 -->|Checked In and In Progress| ATT32[See timer and My Schedule]
    ATT29 -->|Creator of event| ATT33[Created event also appears in My]

    ATT31 --> ATT34{Paid event?}
    ATT34 -- Yes --> ATT35[Show no-refund warning<br/>then cancel without refund]
    ATT34 -- No --> ATT36[Cancel directly]
    ATT35 --> ATT37[POST /events/:id/cancel-registration]
    ATT36 --> ATT37
    ATT37 --> ATT38[Refresh event list]

    ATT27 --> ATT39[If spot opens, backend may auto-register first waitlisted user]
    ATT39 --> ATT40[No automatic notification is currently sent]

    ATT32 --> ATT41[Round Timer card]
    ATT41 --> ATT42{Timer state}
    ATT42 -->|Inactive| ATT43[Show Event will be starting shortly]
    ATT42 -->|Active| ATT44[Show round countdown]
    ATT42 -->|Paused| ATT45[Show paused]
    ATT42 -->|Break| ATT46[Show get to your table for next round]

    ATT32 --> ATT47[Open My Schedule accordion]
    ATT47 --> ATT48[GET /events/:id/schedule]
    ATT48 --> ATT49{Schedule item for round exists?}
    ATT49 -- Yes --> ATT50[Show round number, table, partner]
    ATT49 -- No --> ATT51[Show Break Round]
    ATT50 --> ATT52[Tap Yes or No]
    ATT52 --> ATT53[Selections also persist in localStorage]
    ATT53 --> ATT54[Save Selections]
    ATT54 --> ATT55{Event still In Progress?}
    ATT55 -- Yes --> ATT56[POST /events/:id/submit-selections]
    ATT55 -- No --> ATT57[Only local save indicator; no submit]

    ATT32 --> ATT58{Event auto-marked Completed later?}
    ATT58 -- Yes --> ATT59[My Schedule hides Yes/No buttons]
    ATT59 --> ATT60[Show partner name as card title]
    ATT60 --> ATT61{Mutual match?}
    ATT61 -- Yes --> ATT62[Show matched message and partner email copy action]
    ATT61 -- No --> ATT63[Show not-a-match message]

    ATT0 --> SH1
  end

  subgraph OrganizerPath[Organizer Path]
    ORG0[Organizer on /events] --> ORG1{Create tab}
    ORG1 --> ORG2{Stripe Connect onboarding complete?}
    ORG2 -- No --> ORG3[Show Stripe setup card]
    ORG3 --> ORG4[POST /connect/onboarding]
    ORG4 --> ORG5[Return with query params]
    ORG5 --> ORG6[POST /organizer-status/refresh]
    ORG6 --> ORG2
    ORG2 -- Yes --> ORG7[Create Event form]
    ORG7 --> ORG8[Enter name, description, local starts_at, capacity, price, address]
    ORG8 --> ORG9[Minimum ticket price enforced from fee schedule]
    ORG9 --> ORG10[POST /events/create]

    ORG0 --> ORG11[Manage only events where creator_id = current organizer]
    ORG11 --> ORG12[View Registered Users]
    ORG12 --> ORG13[Search users]
    ORG12 --> ORG14[Edit attendee first name, last name, email, gender, church]
    ORG12 --> ORG15[Manual Check In registered attendee]
    ORG12 --> ORG16[Organizer cannot export registered-users CSV in current UI]

    ORG11 --> ORG17[View Waitlist]
    ORG17 --> ORG18[Search waitlist]
    ORG17 --> ORG19[Move waitlisted user to registered]
    ORG19 --> ORG20[Current code registers directly and bypasses Stripe]
    ORG17 --> ORG21[Export waitlist CSV]

    ORG11 --> ORG22[Edit Event]
    ORG22 --> ORG23[Edit name, description, starts_at, address, capacity, price, status]
    ORG23 --> ORG24[PUT /events/:id]

    ORG11 --> ORG25[Delete Event button]
    ORG25 --> ORG26{Event status In Progress or Completed?}
    ORG26 -- Yes --> ORG27[Delete button disabled in UI]
    ORG26 -- No --> ORG28[DELETE /events/:id]

    ORG11 --> ORG29[Generate Schedules]
    ORG29 --> ORG30[Enter requested tables and rounds]
    ORG30 --> ORG31[POST /events/:id/generate/schedules]
    ORG31 --> ORG32{Schedule generated?}
    ORG32 -- No --> ORG33[Show failure]
    ORG32 -- Yes --> ORG34[Existing speed dates deleted]
    ORG34 --> ORG35[Event status set to In Progress]
    ORG35 --> ORG36[Event num_rounds and num_tables set to actual values]
    ORG36 --> ORG37[Fresh timer record created]

    ORG11 --> ORG38{Event status In Progress or Completed?}
    ORG38 -- Yes --> ORG39[View All Schedules]
    ORG39 --> ORG40[Search and sort schedules]
    ORG39 --> ORG41[Export schedules CSV]

    ORG35 --> ORG42[Organizer timer controls]
    ORG42 --> ORG43{Timer state}
    ORG43 -->|Inactive| ORG44[Start Round 1]
    ORG43 -->|Active| ORG45[End Round or Pause Round]
    ORG43 -->|Paused| ORG46[Resume Round]
    ORG43 -->|Break| ORG47[Start next round]
    ORG43 -->|Inactive or Break| ORG48[Open settings and change round duration only]
    ORG45 --> ORG49[Ending round forces break_time or final completion state]
    ORG47 --> ORG50[UI calls next-round then start-round]
    ORG50 --> ORG42

    ORG11 --> ORG51[Organizer can also personally use attendee registration flow for events]
    ORG0 --> SH1
  end

  subgraph AdminPath[Admin Path]
    ADM0[Admin on /events<br/>admin account created manually outside signup] --> ADM1[Create Event without Stripe onboarding]
    ADM1 --> ADM2[POST /events/create]

    ADM0 --> ADM3[Manage any event]
    ADM3 --> ADM4[View Registered Users]
    ADM4 --> ADM5[Search users]
    ADM4 --> ADM6[Edit attendee details]
    ADM4 --> ADM7[Manual Check In]
    ADM4 --> ADM8[Export registered-users CSV]

    ADM3 --> ADM9[View Waitlist]
    ADM9 --> ADM10[Move waitlisted user to registered]
    ADM9 --> ADM11[Export waitlist CSV]

    ADM3 --> ADM12[Edit any event including status]
    ADM12 --> ADM13[PUT /events/:id]

    ADM3 --> ADM14[Generate schedules for any Registration Open event]
    ADM14 --> ADM15[Timer controls identical to organizer controls]
    ADM15 --> ADM16[View All Schedules]
    ADM16 --> ADM17[Export schedules CSV]

    ADM3 --> ADM18[UI delete button disabled for In Progress and Completed events]
    ADM3 --> ADM19[Backend delete route still allows admin deletion of any event]
    ADM19 --> ADM20[DELETE /events/:id]

    ADM0 --> ADM21[Backend-only admin endpoints]
    ADM21 --> ADM22[GET /admin/users]
    ADM21 --> ADM23[PUT /admin/users/:id/role]
    ADM21 --> ADM24[GET /admin/check]

    ADM0 --> ADM25[Admin can also use attendee registration flow for events]
    ADM0 --> SH1
  end

  subgraph MaintenanceFlow[Background Maintenance]
    MT0([Daily 9:00 AM Eastern cron]) --> MT1[Run auto_complete_due_events.py]
    MT1 --> MT2[Find all In Progress events]
    MT2 --> MT3{Event start date in America/New_York is before current Eastern date?}
    MT3 -- Yes --> MT4[Set event status to Completed]
    MT3 -- No --> MT5[Leave event unchanged]
    MT4 --> ATT59
    MT4 --> ORG39
    MT4 --> ADM16
  end
```

## Matching Algorithm Flow

```mermaid
flowchart TD
  MA0([Generate schedule request]) --> MA1[Delete existing EventSpeedDate rows for this event]
  MA1 --> MA2[Load checked-in attendees only]
  MA2 --> MA3{At least 2 attendees?}
  MA3 -- No --> MA4[Return failure -1, -1]
  MA3 -- Yes --> MA5[Split attendees into males and females]
  MA5 --> MA6{At least 1 male and 1 female?}
  MA6 -- No --> MA4
  MA6 -- Yes --> MA7[Adjust tables to min requested tables and smaller gender count]
  MA7 --> MA8[Initialize all_compatible_dates and id_to_user]

  MA8 --> MA9[For each attendee]
  MA9 --> MA10[Choose opposite-gender pool]
  MA10 --> MA11[Query all historical EventSpeedDate rows involving this attendee]
  MA11 --> MA12[Build previous_date_user_ids]
  MA12 --> MA13[Initial compatible list:<br/>different church unless one side has no church<br/>age diff <= 3<br/>never speed-dated before]
  MA13 --> MA14[Compute min_dates_threshold based on tables, rounds, same-gender count]
  MA14 --> MA15{Enough compatible dates?}
  MA15 -- Yes --> MA20[Store compatible dates for attendee]
  MA15 -- No --> MA16[Retry with age diff <= 4]
  MA16 --> MA17{Enough now?}
  MA17 -- Yes --> MA20
  MA17 -- No --> MA18[Retry with age diff <= 5]
  MA18 --> MA19{Enough now?}
  MA19 -- Yes --> MA20
  MA19 -- No --> MA21[Final fallback:<br/>allow same church<br/>keep age diff <= 5<br/>still exclude all previous dates]
  MA21 --> MA20

  MA20 --> MA22{More attendees to process?}
  MA22 -- Yes --> MA9
  MA22 -- No --> MA23[Initialize rounds_completed_per_attendee = 0]

  MA23 --> MA24[For round 1..requested rounds]
  MA24 --> MA25[Sort attendee ids by:<br/>1. fewest completed rounds<br/>2. fewest compatible dates]
  MA25 --> MA26[Reset attendees_seated_this_round]
  MA26 --> MA27[Reset available tables 1..num_tables_adjusted]
  MA27 --> MA28[For each sorted attendee]
  MA28 --> MA29{Already seated this round?}
  MA29 -- Yes --> MA28
  MA29 -- No --> MA30[Sort this attendee's compatible dates by:<br/>1. fewest completed rounds<br/>2. smallest age difference]
  MA30 --> MA31[Scan for first compatible date not already seated this round]
  MA31 --> MA32{Found available compatible partner?}
  MA32 -- No --> MA39[Attendee sits out this round]
  MA32 -- Yes --> MA33[Assign male_id and female_id from genders]
  MA33 --> MA34{Reusable previous-round table available for one of these participants and still open?}
  MA34 -- Yes --> MA35[Reuse that table]
  MA34 -- No --> MA36[Take first available table]
  MA35 --> MA37[Create EventSpeedDate for this round and table]
  MA36 --> MA37
  MA37 --> MA38[Mark both attendees seated and increment both round counters]
  MA38 --> MA40[Remove each other from both compatible lists so this pair cannot repeat in this event]
  MA40 --> MA41{Any tables left this round?}
  MA41 -- No --> MA42[End current round early]
  MA41 -- Yes --> MA28
  MA39 --> MA41
  MA42 --> MA43{More rounds requested?}
  MA43 -- Yes --> MA24
  MA43 -- No --> MA44[Persist all generated EventSpeedDate rows]
  MA44 --> MA45[Return actual max round used and adjusted table count]
```
