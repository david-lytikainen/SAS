## App Flow

```mermaid
flowchart TD
  subgraph SignupFlow[Start 1: Sign Up]
    SU0([Sign Up]) --> SU1[Enter first name<br/>last name email phone<br/>birthday gender church<br/>password confirm password]
    SU1 --> SU2{Frontend validation passes?}
    SU2 -- No --> SU3[Show validation error]
    SU2 -- Yes --> SU4[POST /api/user/signup]
    SU4 --> SU5{Signup accepted?}
    SU5 -- No --> SU6[Show API error]
    SU5 -- Yes --> SU7[Signup response already includes JWT and user]
    SU7 --> SU8[AuthContext stores token in localStorage]
    SU8 --> SU9[Navigate to /events]
    SU9 --> SU10{Signup path}
    SU10 -->|Attendee only| ATT0
    SU10 -->|Future organizer path| ORGSU0
  end

  subgraph SigninFlow[Start 2: Sign In]
    SI0([Sign In]) --> SI1[Enter email and password]
    SI1 --> SI2{Credentials valid?}
    SI2 -- No --> SI3[Show login error]
    SI3 --> SI4[Optional Forgot Password]
    SI4 --> SI5[POST /api/user/forgot-password]
    SI5 --> SI6[Open reset link]
    SI6 --> SI7[POST /api/user/reset-password/:token]
    SI2 -- Yes --> SI8[Response returns JWT and user]
    SI8 --> SI9[AuthContext stores token in localStorage]
    SI9 --> SI10[Navigate to /events]
    SI10 --> SI11{Role on sign in}
    SI11 -->|Attendee| ATT0
    SI11 -->|Organizer| ORG0
    SI11 -->|Admin| ADM0
  end

  subgraph SharedAuth[Shared Auth and Profile]
    SA0[Later visit with persistLogin true] --> SA1[Read token from localStorage]
    SA1 --> SA2[GET /api/user/validate-token]
    SA2 --> SA3{Token valid?}
    SA3 -- Yes --> SA4[Restore user session]
    SA3 -- No --> SA5[Clear token and stay signed out]

    SP0[/events/] --> SP1[Top-right username]
    SP1 --> SP2[/profile/]
    SP2 --> SP3[Read-only profile rows]
    SP3 --> SP4[Header pencil enables edit mode]
    SP4 --> SP5[PATCH /api/user/profile]
    SP2 --> SP6[Logout clears token and user state]
    SP2 --> SP7{Role 2 or 3?}
    SP7 -- Yes --> SP8[Show Billing card<br/>GET /api/user/profile/dashboard]
    SP7 -- No --> SP9[Profile only]
    SP8 --> SP10{Role 3 admin?}
    SP10 -- Yes --> SP11[Show Admin Tools<br/>latest scheduler runs<br/>recent failures]
  end

  subgraph AttendeePath[Attendee Path]
    ATT0[Events page] --> ATT1{Attendee checked in to an In Progress event?}
    ATT1 -- Yes --> ATT2[EventContext shows only that one active event]
    ATT1 -- No --> ATT3[Show normal event list<br/>mock events hidden]
    ATT2 --> ATT4{Tab}
    ATT3 --> ATT4
    ATT4 -->|My| ATT5[Show registered waitlisted and created events]
    ATT4 -->|All| ATT6[Show all visible events]
    ATT4 -->|Create| ATT7[Show Stripe organizer setup card]

    ATT7 --> ATT8[Continue to Stripe]
    ATT8 --> ATT9[POST /api/user/connect/onboarding]
    ATT9 --> ATT10[Return to /events?view=create&amp;stripe_connect=return]
    ATT10 --> ATT11[POST /api/user/organizer-status/refresh]
    ATT11 --> ATT12[Refresh user]
    ATT12 --> ORG0

    ATT5 --> ATT13{Any visible My events?}
    ATT13 -- No --> ATT14[Show switch to All hint]
    ATT5 --> ATT15[Past Events accordion available]
    ATT6 --> ATT15

    ATT6 --> ATT16{Event card state}
    ATT16 -->|Registration Open and not registered| ATT17[Sign Up]
    ATT16 -->|Waitlisted| ATT18[Waitlisted chip<br/>Leave Waitlist]
    ATT16 -->|Registered before start| ATT19[Registered chip<br/>Cancel Registration]
    ATT16 -->|Checked In before start| ATT20[Checked In chip]
    ATT16 -->|In Progress with registration record| ATT21[Show round timer card]
    ATT16 -->|In Progress without registration| ATT22[Read-only event card]
    ATT16 -->|Completed or older than 48h| ATT23[Move card into Past Events]

    ATT17 --> ATT24[Open confirm dialog]
    ATT24 --> ATT25{Paid event?}
    ATT25 -- No --> ATT26[POST /api/events/:id/register<br/>join_waitlist false]
    ATT26 --> ATT27{Registration outcome}
    ATT27 -- Success --> ATT28[Refresh events and show Registered]
    ATT27 -- Full or gender cap --> ATT29[Open waitlist dialog]
    ATT27 -- Other error --> ATT30[Show API error]

    ATT25 -- Yes --> ATT31[POST /api/events/:id/checkout]
    ATT31 --> ATT32{Checkout created?}
    ATT32 -- No --> ATT33{Full or gender cap?}
    ATT33 -- Yes --> ATT29
    ATT33 -- No --> ATT30
    ATT32 -- Yes --> ATT34[Redirect browser to Stripe Checkout]
    ATT34 --> ATT35[Stripe webhook<br/>checkout.session.completed]
    ATT35 --> ATT36[Upsert EventPayment]
    ATT36 --> ATT37[Webhook calls register_for_event<br/>payment_confirmed true]
    ATT37 --> ATT38{Webhook registration outcome}
    ATT38 -- Success --> ATT39[Mark payment registered<br/>queue confirmation email]
    ATT38 -- Failure --> ATT40[Mark registration_failed]
    ATT40 --> ATT41[Try automatic full refund]
    ATT41 --> ATT42{Refund outcome}
    ATT42 -- Success --> ATT43[Mark registration_failed_refunded]
    ATT42 -- Failure --> ATT44[Mark refund_failed for support]

    ATT29 --> ATT45{Join waitlist?}
    ATT45 -- Yes --> ATT46[POST /api/events/:id/register<br/>join_waitlist true]
    ATT46 --> ATT47[Refresh events and show Waitlisted]
    ATT45 -- No --> ATT48[Stay unregistered]

    ATT18 --> ATT49[POST /api/events/:id/cancel-registration]
    ATT49 --> ATT50[Removed from waitlist]

    ATT19 --> ATT51[Open cancel dialog]
    ATT51 --> ATT52{Paid event?}
    ATT52 -- Yes --> ATT53[Warn no refund through app]
    ATT52 -- No --> ATT54[Cancel directly]
    ATT53 --> ATT55[POST /api/events/:id/cancel-registration]
    ATT54 --> ATT55
    ATT55 --> ATT56[Refresh events]
    ATT56 --> ATT57{Spot now open?}
    ATT57 -- Yes --> ATT58[Eligible waitlisted users stay waitlisted<br/>and get spot-open email]
    ATT57 -- No --> ATT59[No waitlist email sent]

    ATT21 --> ATT60{Viewer}
    ATT60 -->|Checked-in attendee| ATT61[Attendee timer view]
    ATT60 -->|Organizer or admin managing event| ORG41
    ATT61 --> ATT62{Timer state}
    ATT62 -->|Inactive| ATT63[Event will be starting shortly]
    ATT62 -->|Active| ATT64[Show round countdown]
    ATT62 -->|Paused| ATT65[Show paused countdown]
    ATT62 -->|Break| ATT66[Show next-round countdown]
    ATT62 -->|Ended| ATT67[Event Finished<br/>Save your selections]

    ATT20 --> ATT68[My Schedule accordion available]
    ATT21 --> ATT68
    ATT68 --> ATT69{Expand while event is In Progress or Completed?}
    ATT69 -- No --> ATT70[Keep accordion closed]
    ATT69 -- Yes --> ATT71[GET /api/events/:id/schedule]
    ATT71 --> ATT72{Schedule returned?}
    ATT72 -- No --> ATT73[Show waiting / no schedule message]
    ATT72 -- Yes --> ATT74{Event status}
    ATT74 -- In Progress --> ATT75[Render each round<br/>partner or break row]
    ATT75 --> ATT76[Tap Yes or No]
    ATT76 --> ATT77[Store selections in localStorage]
    ATT77 --> ATT78[Save Selections]
    ATT78 --> ATT79[POST /api/events/:id/submit-selections]
    ATT79 --> ATT80{Checked in and event still In Progress?}
    ATT80 -- Yes --> ATT81[Persist interest on EventSpeedDate]
    ATT80 -- No --> ATT82[Show API error]

    ATT74 -- Completed --> ATT83[Hide Yes/No buttons<br/>hide break-only rows]
    ATT83 --> ATT84[Show partner card titles]
    ATT84 --> ATT85{Mutual match on row?}
    ATT85 -- Yes --> ATT86[Show match message and partner email]
    ATT85 -- No --> ATT87[Show not-a-match message]

    ATT0 --> SP1
  end

  subgraph OrganizerPath[Organizer Path]
    ORGSU0[Future organizer from sign up] --> ORG0
    ORG0[Organizer on /events] --> ORG1{Create tab}
    ORG1 --> ORG2{Stripe Connect complete?}
    ORG2 -- No --> ORG3[Show setup card<br/>Continue to Stripe<br/>Check Setup]
    ORG3 --> ORG4[POST /api/user/connect/onboarding]
    ORG4 --> ORG5[Return to create tab]
    ORG5 --> ORG6[POST /api/user/organizer-status/refresh]
    ORG6 --> ORG2
    ORG2 -- Yes --> ORG7[Show Create Event form]
    ORG7 --> ORG8[Enter name description<br/>local start datetime address<br/>capacity price 60/40 toggle]
    ORG8 --> ORG9[Price floor enforced for early organizer events]
    ORG9 --> ORG10[POST /api/events/create]

    ORG0 --> ORG11[My or All tabs]
    ORG11 --> ORG12[Manage only events they created]
    ORG12 --> ORG13[Expand Event Controls]

    ORG13 --> ORG14[View Registered Users]
    ORG14 --> ORG15[GET /api/events/:id/attendees]
    ORG15 --> ORG16[Search by first or last name prefix]
    ORG15 --> ORG17[Edit attendee fields]
    ORG15 --> ORG18[Manual check in attendee]
    ORG15 --> ORG19[Export registered CSV]

    ORG13 --> ORG20[View Waitlist]
    ORG20 --> ORG21[GET /api/events/:id/waitlist]
    ORG21 --> ORG22[Search by first name last name or email prefix]
    ORG21 --> ORG23[Export waitlist CSV]

    ORG13 --> ORG24[Edit Event]
    ORG24 --> ORG25[Edit name description<br/>datetime address capacity<br/>price 60/40 toggle]
    ORG25 --> ORG26[PUT /api/events/:id]

    ORG13 --> ORG27[Delete Event]
    ORG27 --> ORG28{Status In Progress or Completed?}
    ORG28 -- Yes --> ORG29[Delete disabled in UI<br/>backend also rejects]
    ORG28 -- No --> ORG30[DELETE /api/events/:id]

    ORG13 --> ORG31[Generate Schedules]
    ORG31 --> ORG32[Choose requested tables and rounds]
    ORG32 --> ORG33[POST /api/events/:id/generate/schedules]
    ORG33 --> ORG34{Generation succeeded?}
    ORG34 -- No --> ORG35[Show failure]
    ORG34 -- Yes --> ORG36[Delete old EventSpeedDate rows]
    ORG36 --> ORG37[Use checked-in attendees only]
    ORG37 --> ORG38[Set event status to In Progress]
    ORG38 --> ORG39[Persist actual rounds and tables]
    ORG39 --> ORG40[Reset EventTimer row]

    ORG13 --> ORG41{Event In Progress or Completed?}
    ORG41 -- Yes --> ORG42[View All Schedules]
    ORG42 --> ORG43[GET /api/events/:id/all-schedules]
    ORG43 --> ORG44[Search by attendee name prefix]
    ORG43 --> ORG45[Sort by user partner round or table]
    ORG43 --> ORG46[Export simplified CSV<br/>Name 1 Name 2 Round Table]

    ORG38 --> ORG47[Manager timer panel]
    ORG47 --> ORG48{Timer state}
    ORG48 -->|Inactive| ORG49[Play starts round]
    ORG48 -->|Active| ORG50[Back restarts or goes previous<br/>Pause pauses<br/>Forward ends round into break]
    ORG48 -->|Paused| ORG51[Play resumes round]
    ORG48 -->|Break| ORG52[Play starts next round<br/>Back restarts current round]
    ORG48 -->|Ended| ORG53[Show Event Finished]
    ORG47 --> ORG54{Active or paused?}
    ORG54 -- No --> ORG55[Settings dialog can change<br/>round and break durations]

    ORG12 --> ORG56[Organizer can still sign up for events as attendee]
    ORG0 --> SP1
  end

  subgraph AdminPath[Admin Path]
    ADM0[Admin on /events] --> ADM1[Create tab opens Create Event form immediately]
    ADM1 --> ADM2[POST /api/events/create]

    ADM0 --> ADM3[Admins can see mock events and manage any event]
    ADM3 --> ADM4[Expand Event Controls]
    ADM4 --> ADM5[View Registered Users]
    ADM5 --> ADM6[Search edit manual check in export CSV]

    ADM4 --> ADM7[View Waitlist]
    ADM7 --> ADM8[Search and export waitlist CSV]

    ADM4 --> ADM9[Edit Event]
    ADM9 --> ADM10[PUT /api/events/:id]

    ADM4 --> ADM11[Generate Schedules]
    ADM11 --> ORG32

    ADM4 --> ADM12[Delete Event]
    ADM12 --> ADM13{Status In Progress or Completed?}
    ADM13 -- Yes --> ADM14[Delete disabled in UI<br/>blocked in backend]
    ADM13 -- No --> ADM15[DELETE /api/events/:id]

    ADM0 --> ADM16[In Progress card always shows manager timer panel]
    ADM16 --> ORG48

    ADM4 --> ADM17[View All Schedules]
    ADM17 --> ADM18[GET /api/events/:id/all-schedules]
    ADM18 --> ADM19[Search sort and export same simplified CSV]

    ADM0 --> ADM20[No manager match visibility flow]
    ADM20 --> ADM21[GET /api/events/:id/all-matches always returns 403]
    ADM0 --> SP1
  end

  subgraph MaintenanceFlow[Background Maintenance]
    MT0([Scheduler startup paths]) --> MT1[start.py]
    MT0 --> MT2[wsgi.py]
    MT0 --> MT3[run_scheduler.py]
    MT1 --> MT4[start_embedded_scheduler helper]
    MT2 --> MT4
    MT3 --> MT4

    MT4 --> MT5{ENABLE_EMBEDDED_SCHEDULER truthy<br/>and not Werkzeug parent?}
    MT5 -- No --> MT6[No scheduler starts]
    MT5 -- Yes --> MT7[Start BackgroundScheduler<br/>America/New_York]

    MT7 --> MT8[9:00 AM Eastern<br/>auto-complete due events]
    MT7 --> MT9[9:00 PM Eastern<br/>send due reminders]
    MT7 --> MT10[Every 15s<br/>process pending email jobs]

    MT8 --> MT11[Try advisory lock 90412025]
    MT11 --> MT12{Lock acquired?}
    MT12 -- No --> MT13[Skip run]
    MT12 -- Yes --> MT14[Find In Progress events]
    MT14 --> MT15{Event Eastern date is before today?}
    MT15 -- Yes --> MT16[Set event status to Completed]
    MT15 -- No --> MT17[Leave event unchanged]
    MT16 --> MT18[Record scheduler_job_runs row]

    MT9 --> MT19[Try advisory lock 90412026]
    MT19 --> MT20{Lock acquired?}
    MT20 -- No --> MT21[Skip run]
    MT20 -- Yes --> MT22[Find future Registration Open events<br/>with Registered or Checked In attendees]
    MT22 --> MT23{Exactly 1 day 1 week or 1 month away<br/>in Eastern date?}
    MT23 -- Yes --> MT24[Queue reminder email job]
    MT23 -- No --> MT25[Skip attendee]
    MT24 --> MT26[Record scheduler_job_runs row]

    MT10 --> MT27[Try advisory lock 90412027]
    MT27 --> MT28{Lock acquired?}
    MT28 -- No --> MT29[Skip run]
    MT28 -- Yes --> MT30[Process due email_jobs]
    MT30 --> MT31[Retry failed sends up to 3 times<br/>5-minute retry delay]
    MT31 --> MT32[Delete sent email_jobs older than 30 days]
    MT32 --> MT33[Record scheduler_job_runs row]

    MT34[GET /api/user/health] --> MT35[Check database connectivity<br/>plus latest auto-complete run]
  end
```

## Matching Algorithm Flow

```mermaid
flowchart TD
  MA0([Generate schedule request]) --> MA1[Delete existing EventSpeedDate rows for this event]
  MA1 --> MA2[Load checked-in attendees only]
  MA2 --> MA3{At least 2 attendees?}
  MA3 -- No --> MA4[Return -1 -1]
  MA3 -- Yes --> MA5[Split attendees into males and females]
  MA5 --> MA6[Set adjusted tables to the smaller of requested tables and smaller gender count]
  MA6 --> MA7{At least 1 male and 1 female?}
  MA7 -- No --> MA4
  MA7 -- Yes --> MA8[Initialize all_compatible_dates and id_to_user]

  MA8 --> MA9[For each attendee]
  MA9 --> MA10[Choose opposite-gender pool]
  MA10 --> MA11[Query every historical EventSpeedDate involving that attendee]
  MA11 --> MA12[Build previous_date_user_ids]
  MA12 --> MA13[Initial compatible list:<br/>different church unless one side has no church<br/>age diff <= 3<br/>never dated before]
  MA13 --> MA14[Compute min_dates_needed from tables rounds and same-gender count]
  MA14 --> MA15{Enough compatible dates?}
  MA15 -- Yes --> MA20[Store compatible dates]
  MA15 -- No --> MA16[Retry with same church rule still enforced<br/>age diff <= 4]
  MA16 --> MA17{Enough now?}
  MA17 -- Yes --> MA20
  MA17 -- No --> MA18[Retry with same church rule still enforced<br/>age diff <= 5]
  MA18 --> MA19{Enough now?}
  MA19 -- Yes --> MA20
  MA19 -- No --> MA191[Final fallback:<br/>allow same church<br/>keep age diff <= 5<br/>still exclude past dates]
  MA191 --> MA20
  MA20 --> MA21{More attendees left?}
  MA21 -- Yes --> MA9
  MA21 -- No --> MA22[Initialize rounds_completed_per_attendee to 0]

  MA22 --> MA23[For round 1 through requested rounds]
  MA23 --> MA24[Sort attendee ids by:<br/>fewest rounds completed<br/>then fewest compatible dates]
  MA24 --> MA25[Reset seated attendees for this round]
  MA25 --> MA26[Reset available tables 1..adjusted tables]
  MA26 --> MA27[For each sorted attendee]
  MA27 --> MA28{Already seated this round?}
  MA28 -- Yes --> MA27
  MA28 -- No --> MA29[Sort this attendee compatible dates by:<br/>fewest rounds completed<br/>then smallest age diff]
  MA29 --> MA30[Find first compatible partner not seated this round]
  MA30 --> MA31{Found partner?}
  MA31 -- No --> MA32[Attendee sits out this round]
  MA31 -- Yes --> MA33[Resolve male_id and female_id from genders]
  MA33 --> MA34{Reusable previous-round table still open for either participant?}
  MA34 -- Yes --> MA35[Reuse that table]
  MA34 -- No --> MA36[Take first available table]
  MA35 --> MA37[Create EventSpeedDate in memory]
  MA36 --> MA37
  MA37 --> MA38[Mark both attendees seated]
  MA38 --> MA39[Increment both round counters]
  MA39 --> MA40[Remove each other from both compatible lists<br/>so pair cannot repeat this event]
  MA40 --> MA41{Any tables left this round?}
  MA41 -- No --> MA42[End round early]
  MA41 -- Yes --> MA27
  MA32 --> MA41
  MA42 --> MA43{More rounds requested?}
  MA43 -- Yes --> MA23
  MA43 -- No --> MA44[Persist all EventSpeedDate rows]
  MA44 --> MA45{Rows persisted and at least one round exists?}
  MA45 -- No --> MA4
  MA45 -- Yes --> MA46[Return actual max round used and adjusted table count]
```
