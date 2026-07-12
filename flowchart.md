## App Flow

```mermaid
flowchart TD
  subgraph SignupFlow[Start 1: Sign Up]
    SU0([Sign Up]) --> SU1[Enter profile, church, password]
    SU1 --> SU2{Frontend valid?}
    SU2 -- No --> SU3[Show validation error]
    SU2 -- Yes --> SU4[POST /api/user/signup]
    SU4 --> SU5{Signup accepted?}
    SU5 -- No --> SU6[Show API error]
    SU5 -- Yes --> SU7[Store JWT and user]
    SU7 --> SU8[Navigate to /events]
    SU8 --> SU9{Post-signup path}
    SU9 -->|Attendee now| ATT0
    SU9 -->|Future organizer later| ORGSU0
  end

  subgraph SigninFlow[Start 2: Sign In]
    SI0([Sign In]) --> SI1[Enter email and password]
    SI1 --> SI2{Credentials valid?}
    SI2 -- No --> SI3[Show login error]
    SI3 --> SI4[Optional Forgot Password]
    SI4 --> SI5[POST /api/user/forgot-password]
    SI5 --> SI6[Open reset link]
    SI6 --> SI7[POST /api/user/reset-password/:token]
    SI2 -- Yes --> SI8[Store JWT and user]
    SI8 --> SI9[Navigate to /events]
    SI9 --> SI10{Role}
    SI10 -->|Attendee| ATT0
    SI10 -->|Organizer| ORG0
    SI10 -->|Admin| ADM0
  end

  subgraph SharedAuth[Shared Auth and Profile]
    SA0[Later visit with persistLogin] --> SA1[Read token from localStorage]
    SA1 --> SA2[GET /api/user/validate-token]
    SA2 --> SA3{Token valid?}
    SA3 -- Yes --> SA4[Restore session]
    SA3 -- No --> SA5[Clear token and stay signed out]

    SP0[/events/] --> SP1[Top-right username]
    SP1 --> SP2[/profile/]
    SP2 --> SP3[Read-only profile fields]
    SP3 --> SP4[Header pencil enables edit mode]
    SP4 --> SP5[PATCH /api/user/profile]
    SP2 --> SP6[Logout clears token and user]
    SP2 --> SP7{Organizer or admin?}
    SP7 -- Yes --> SP8[Billing card via /api/user/profile/dashboard]
    SP7 -- No --> SP9[Profile only]
    SP8 --> SP10{Admin?}
    SP10 -- Yes --> SP11[Admin Tools with latest scheduler runs and failures]
  end

  subgraph AttendeePath[Attendee Path]
    ATT0[Events page] --> ATT1{Checked in to an In Progress event?}
    ATT1 -- Yes --> ATT2[Show only that active event]
    ATT1 -- No --> ATT3[Show normal event list]
    ATT2 --> ATT4{Tab}
    ATT3 --> ATT4
    ATT4 -->|My| ATT5[My events]
    ATT4 -->|All| ATT6[All events]
    ATT4 -->|Create| ATT7[Organizer setup card]

    ATT7 --> ATT8[Continue to Stripe]
    ATT8 --> ATT9[POST /api/user/connect/onboarding]
    ATT9 --> ATT10[Return with stripe_connect=return]
    ATT10 --> ATT11[POST /api/user/organizer-status/refresh]
    ATT11 --> ATT12[Refresh user]
    ATT12 --> ORG0

    ATT5 --> ATT13{Any visible My events?}
    ATT13 -- No --> ATT14[Show switch-to-All hint]
    ATT5 --> ATT15[Past Events accordion available]
    ATT6 --> ATT15

    ATT6 --> ATT16{Event card state}
    ATT16 -->|Registration Open, not registered| ATT17[Sign Up]
    ATT16 -->|Waitlisted| ATT18[Waitlisted chip and Leave Waitlist]
    ATT16 -->|Registered before start| ATT19[Registered chip and Cancel Registration]
    ATT16 -->|Checked In before start| ATT20[Checked In chip]
    ATT16 -->|In Progress with registration| ATT21[Timer card]
    ATT16 -->|In Progress without registration| ATT22[Read-only card]
    ATT16 -->|Completed or older than 48h| ATT23[Move to Past Events]

    ATT17 --> ATT24[Open confirm dialog]
    ATT24 --> ATT25{Paid event?}
    ATT25 -- No --> ATT26[POST /api/events/:id/register<br/>join_waitlist false]
    ATT26 --> ATT27{Registration outcome}
    ATT27 -- Success --> ATT28[Refresh events and show Registered]
    ATT27 -- Full or gender-full --> ATT29[Open waitlist dialog]
    ATT27 -- Other error --> ATT30[Show API error]

    ATT25 -- Yes --> ATT31[POST /api/events/:id/checkout]
    ATT31 --> ATT32{Checkout created?}
    ATT32 -- No, waitlist available --> ATT29
    ATT32 -- No, other error --> ATT30
    ATT32 -- Yes --> ATT33[Redirect to Stripe Checkout]
    ATT33 --> ATT34[Return with checkout=success and session_id]
    ATT34 --> ATT35[POST /api/events/checkout/complete]
    ATT35 --> ATT36{Session completion result}
    ATT36 -- Success --> ATT37[Refresh events repeatedly until registration shows]
    ATT36 -- Failure --> ATT38[Show checkout verification error]
    ATT33 --> ATT39[Webhook checkout.session.completed]
    ATT39 --> ATT40[Upsert EventPayment]
    ATT40 --> ATT41[Finalize registration with payment_confirmed true]
    ATT41 --> ATT42{Webhook registration result}
    ATT42 -- Success --> ATT43[Mark payment registered and queue confirmation email]
    ATT42 -- Failure --> ATT44[Mark registration_failed and try full refund]
    ATT44 --> ATT45{Refund success?}
    ATT45 -- Yes --> ATT46[Mark registration_failed_refunded]
    ATT45 -- No --> ATT47[Mark refund_failed for support]

    ATT29 --> ATT48{Join waitlist?}
    ATT48 -- Yes --> ATT49[POST /api/events/:id/register<br/>join_waitlist true]
    ATT49 --> ATT50[Refresh events and show Waitlisted]
    ATT48 -- No --> ATT51[Stay unregistered]

    ATT18 --> ATT52[POST /api/events/:id/cancel-registration]
    ATT52 --> ATT53[Remove waitlist row and refresh]

    ATT19 --> ATT54[Open cancel dialog]
    ATT54 --> ATT55{Paid event?}
    ATT55 -- Yes --> ATT56[Warn no in-app refund]
    ATT55 -- No --> ATT57[Cancel directly]
    ATT56 --> ATT58[POST /api/events/:id/cancel-registration]
    ATT57 --> ATT58
    ATT58 --> ATT59[Refresh events]
    ATT59 --> ATT60{Seat opened?}
    ATT60 -- Yes --> ATT61[Eligible waitlisted users stay waitlisted and get spot-open email]
    ATT60 -- No --> ATT62[No waitlist email]

    ATT19 --> ATT63[At venue, organizer/admin must manually check in attendee]
    ATT20 --> ATT64[My Schedule accordion available]
    ATT21 --> ATT64

    ATT21 --> ATT65{Viewer}
    ATT65 -->|Checked-in attendee| ATT66[Attendee timer view]
    ATT65 -->|Organizer or admin manager| ORG41
    ATT66 --> ATT67{Timer state}
    ATT67 -->|Inactive| ATT68[Event will be starting shortly]
    ATT67 -->|Active| ATT69[Show round countdown]
    ATT67 -->|Paused| ATT70[Show paused countdown]
    ATT67 -->|Break| ATT71[Show break countdown]
    ATT67 -->|Ended| ATT72[Event Finished, save selections]

    ATT64 --> ATT73{Expand while In Progress or Completed?}
    ATT73 -- No --> ATT74[Keep accordion closed]
    ATT73 -- Yes --> ATT75[GET /api/events/:id/schedule]
    ATT75 --> ATT76{Schedule returned?}
    ATT76 -- No --> ATT77[Show waiting / no schedule message]
    ATT76 -- Yes --> ATT78{Event status}
    ATT78 -- In Progress --> ATT79[Show round rows with partner or break]
    ATT79 --> ATT80[Tap Yes or No]
    ATT80 --> ATT81[Store selections in localStorage]
    ATT81 --> ATT82[Save Selections]
    ATT82 --> ATT83[POST /api/events/:id/submit-selections]
    ATT83 --> ATT84{Checked-in attendee and event still In Progress?}
    ATT84 -- Yes --> ATT85[Persist interest on EventSpeedDate]
    ATT84 -- No --> ATT86[Show API error]

    ATT78 -- Completed --> ATT87[Hide Yes/No and break-only rows]
    ATT87 --> ATT88[Show partner cards]
    ATT88 --> ATT89{Mutual match on row?}
    ATT89 -- Yes --> ATT90[Show match message and partner email]
    ATT89 -- No --> ATT91[Show not-a-match message]

    ATT0 --> SP1
  end

  subgraph OrganizerPath[Organizer Path]
    ORGSU0[Future organizer path] --> ORG0
    ORG0[Organizer on /events] --> ORG1{Create tab}
    ORG1 --> ORG2{Stripe Connect complete?}
    ORG2 -- No --> ORG3[Show setup card, Continue to Stripe, Check Setup]
    ORG3 --> ORG4[POST /api/user/connect/onboarding]
    ORG4 --> ORG5[Return to create tab]
    ORG5 --> ORG6[POST /api/user/organizer-status/refresh]
    ORG6 --> ORG2
    ORG2 -- Yes --> ORG7[Show Create Event form]
    ORG7 --> ORG8[Enter name, description, datetime, address, capacity, price, 60/40 toggle]
    ORG8 --> ORG9[POST /api/events/create]

    ORG0 --> ORG10[My or All tabs]
    ORG10 --> ORG11[Manage only created events]
    ORG11 --> ORG12[Expand Event Controls]

    ORG12 --> ORG13[View Registered Users]
    ORG13 --> ORG14[GET /api/events/:id/attendees]
    ORG14 --> ORG15[Search by first or last name prefix]
    ORG14 --> ORG16[Edit attendee fields]
    ORG14 --> ORG17[Manual check in attendee]
    ORG14 --> ORG18[Export registered CSV]

    ORG12 --> ORG19[View Waitlist]
    ORG19 --> ORG20[GET /api/events/:id/waitlist]
    ORG20 --> ORG21[Search by first name, last name, or email prefix]
    ORG20 --> ORG22[Export waitlist CSV]

    ORG12 --> ORG23[Edit Event]
    ORG23 --> ORG24[Edit name, description, datetime, address, capacity, price, 60/40 toggle]
    ORG24 --> ORG25[PUT /api/events/:id]

    ORG12 --> ORG26[Delete Event]
    ORG26 --> ORG27{In Progress or Completed?}
    ORG27 -- Yes --> ORG28[Delete disabled in UI and rejected in backend]
    ORG27 -- No --> ORG29[DELETE /api/events/:id]

    ORG12 --> ORG30[Generate Schedules]
    ORG30 --> ORG31[Choose requested tables and rounds]
    ORG31 --> ORG32[POST /api/events/:id/generate/schedules]
    ORG32 --> ORG33{Generation succeeded?}
    ORG33 -- No --> ORG34[Show failure]
    ORG33 -- Yes --> ORG35[Delete old EventSpeedDate rows]
    ORG35 --> ORG36[Use checked-in attendees only]
    ORG36 --> ORG37[Set event status to In Progress]
    ORG37 --> ORG38[Persist actual rounds and tables]
    ORG38 --> ORG39[Reset EventTimer row]

    ORG12 --> ORG41{Event In Progress or Completed?}
    ORG41 -- Yes --> ORG42[View All Schedules]
    ORG42 --> ORG43[GET /api/events/:id/all-schedules]
    ORG43 --> ORG44[Search by attendee name prefix]
    ORG43 --> ORG45[Sort by attendee, partner, round, or table]
    ORG43 --> ORG46[Export simplified CSV]

    ORG37 --> ORG47[Manager timer panel]
    ORG47 --> ORG48{Timer state}
    ORG48 -->|Inactive| ORG49[Play starts round]
    ORG48 -->|Active| ORG50[Back restarts, Pause pauses, Forward ends round]
    ORG48 -->|Paused| ORG51[Play resumes round]
    ORG48 -->|Break| ORG52[Play starts next round, Back restarts current round]
    ORG48 -->|Ended| ORG53[Show Event Finished]
    ORG47 --> ORG54{Inactive or ended?}
    ORG54 -- Yes --> ORG55[Settings dialog can change round and break durations]
    ORG54 -- No --> ORG56[Settings hidden while live]

    ORG11 --> ORG57[Organizer can still sign up for events as attendee]
    ORG0 --> SP1
  end

  subgraph AdminPath[Admin Path]
    ADM0[Admin on /events] --> ADM1[Create tab opens Create Event form immediately]
    ADM1 --> ADM2[POST /api/events/create]

    ADM0 --> ADM3[Admins can see mock events and manage any event]
    ADM3 --> ADM4[Expand Event Controls]
    ADM4 --> ADM5[View Registered Users]
    ADM5 --> ADM6[Search, edit, manual check in, export CSV]
    ADM4 --> ADM7[View Waitlist]
    ADM7 --> ADM8[Search and export waitlist CSV]
    ADM4 --> ADM9[Edit Event]
    ADM9 --> ADM10[PUT /api/events/:id]
    ADM4 --> ADM11[Generate Schedules]
    ADM11 --> ORG31
    ADM4 --> ADM12[Delete Event]
    ADM12 --> ADM13{In Progress or Completed?}
    ADM13 -- Yes --> ADM14[Delete disabled in UI and blocked in backend]
    ADM13 -- No --> ADM15[DELETE /api/events/:id]
    ADM0 --> ADM16[In Progress card always shows manager timer panel]
    ADM16 --> ORG48
    ADM4 --> ADM17[View All Schedules]
    ADM17 --> ADM18[GET /api/events/:id/all-schedules]
    ADM18 --> ADM19[Search, sort, and export same simplified CSV]
    ADM0 --> SP1
  end

  subgraph MaintenanceFlow[Background Maintenance]
    MT0([Scheduler startup paths]) --> MT1[start.py]
    MT0 --> MT2[wsgi.py]
    MT0 --> MT3[run_scheduler.py]
    MT1 --> MT4[start_embedded_scheduler]
    MT2 --> MT4
    MT3 --> MT4

    MT4 --> MT5{ENABLE_EMBEDDED_SCHEDULER enabled and not Werkzeug parent?}
    MT5 -- No --> MT6[Do not start scheduler]
    MT5 -- Yes --> MT7[Start BackgroundScheduler in America/New_York]

    MT7 --> MT8[9:00 AM Eastern auto-complete job]
    MT7 --> MT9[9:00 PM Eastern reminder job]
    MT7 --> MT10[Every 15 minutes email-job processor]

    MT8 --> MT11[Try advisory lock 90412025]
    MT11 --> MT12{Lock acquired?}
    MT12 -- No --> MT13[Skip run]
    MT12 -- Yes --> MT14[Find In Progress events]
    MT14 --> MT15{Eastern event date before today?}
    MT15 -- Yes --> MT16[Set event to Completed]
    MT15 -- No --> MT17[Leave unchanged]
    MT16 --> MT18[Record scheduler_job_runs row]

    MT9 --> MT19[Try advisory lock 90412026]
    MT19 --> MT20{Lock acquired?}
    MT20 -- No --> MT21[Skip run]
    MT20 -- Yes --> MT22[Find future Registration Open events with Registered or Checked In attendees]
    MT22 --> MT23{Exactly 1 day, 1 week, or 1 month away in Eastern date?}
    MT23 -- Yes --> MT24[Queue reminder email job]
    MT23 -- No --> MT25[Skip attendee]
    MT24 --> MT26[Record scheduler_job_runs row]

    MT10 --> MT27[Try advisory lock 90412027]
    MT27 --> MT28{Lock acquired?}
    MT28 -- No --> MT29[Skip run]
    MT28 -- Yes --> MT30[Process due email_jobs]
    MT30 --> MT31[Retry failed sends up to 3 times with 5-minute delay]
    MT31 --> MT32[Delete sent jobs older than 30 days]
    MT32 --> MT33[Record scheduler_job_runs row]

    MT34[GET /api/user/health] --> MT35[Check DB connectivity]
    MT35 --> MT36[Include embedded-enabled flag]
    MT36 --> MT37[Include latest auto-complete, reminder, and email-job runs]
  end
```

## Matching Algorithm Flow

```mermaid
flowchart TD
  MA0([Generate schedule request]) --> MA1[Delete existing EventSpeedDate rows]
  MA1 --> MA2[Load checked-in attendees only]
  MA2 --> MA3{At least 2 attendees?}
  MA3 -- No --> MA4[Return -1, -1]
  MA3 -- Yes --> MA5[Split attendees into males and females]
  MA5 --> MA6[Adjusted tables = min requested tables and smaller gender count]
  MA6 --> MA7{At least 1 male and 1 female?}
  MA7 -- No --> MA4
  MA7 -- Yes --> MA8[Initialize compatible-date map and id map]

  MA8 --> MA9[For each attendee]
  MA9 --> MA10[Pick opposite-gender pool]
  MA10 --> MA11[Load historical EventSpeedDate rows involving attendee]
  MA11 --> MA12[Build previous-date user ids]
  MA12 --> MA13[Initial filter:<br/>different church unless one side missing church<br/>age diff <= 3<br/>never dated before]
  MA13 --> MA14[Compute min_dates_needed = floor ceil tables x rounds / same-gender count]
  MA14 --> MA15{Enough compatible dates?}
  MA15 -- Yes --> MA20[Store compatible dates]
  MA15 -- No --> MA16[Retry with age diff <= 4 and same church rule]
  MA16 --> MA17{Enough now?}
  MA17 -- Yes --> MA20
  MA17 -- No --> MA18[Retry with age diff <= 5 and same church rule]
  MA18 --> MA19{Enough now?}
  MA19 -- Yes --> MA20
  MA19 -- No --> MA191[Final fallback:<br/>allow same church<br/>keep age diff <= 5<br/>still exclude past dates]
  MA191 --> MA20
  MA20 --> MA21{More attendees left?}
  MA21 -- Yes --> MA9
  MA21 -- No --> MA22[Initialize rounds_completed_per_attendee = 0]

  MA22 --> MA23[For round 1 through requested rounds]
  MA23 --> MA24[Sort attendee ids by fewest rounds completed, then fewest compatible dates]
  MA24 --> MA25[Reset seated-attendee set]
  MA25 --> MA26[Reset available tables 1..adjusted tables]
  MA26 --> MA27[For each sorted attendee]
  MA27 --> MA28{Already seated this round?}
  MA28 -- Yes --> MA27
  MA28 -- No --> MA29[Sort this attendee compatible dates by fewest rounds completed, then smallest age diff]
  MA29 --> MA30[Find first compatible partner not already seated]
  MA30 --> MA31{Found partner?}
  MA31 -- No --> MA41
  MA31 -- Yes --> MA32[Resolve male_id and female_id]
  MA32 --> MA33{Reusable previous-round table available?}
  MA33 -- Yes --> MA34[Reuse that table]
  MA33 -- No --> MA35[Take first available table]
  MA34 --> MA36[Append in-memory EventSpeedDate]
  MA35 --> MA36
  MA36 --> MA37[Mark both attendees seated]
  MA37 --> MA38[Increment both round counters]
  MA38 --> MA39[Remove each other from both compatible lists for this event]
  MA39 --> MA40[Break to next attendee]
  MA40 --> MA41{Any tables left this round?}
  MA41 -- No --> MA42[End round early]
  MA41 -- Yes --> MA27
  MA42 --> MA43{More rounds requested?}
  MA43 -- Yes --> MA23
  MA43 -- No --> MA44[Add all generated EventSpeedDate rows to DB session]
  MA44 --> MA45[Commit transaction]
  MA45 --> MA46[Compute max round from generated rows]
  MA46 --> MA47{Max round available?}
  MA47 -- Yes --> MA48[Return max round and adjusted table count]
  MA47 -- No --> MA4
```
