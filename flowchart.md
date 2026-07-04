## App Flow

```mermaid
flowchart TD
  subgraph SignupFlow[Start 1: Sign Up]
    SU0([Sign Up]) --> SU1[Enter first name last name email phone birthday gender church password confirm password]
    SU1 --> SU2{Frontend validation passes?}
    SU2 -- No --> SU3[Show validation error]
    SU2 -- Yes --> SU4[POST /api/user/signup]
    SU4 --> SU5{Signup accepted?}
    SU5 -- No --> SU6[Show API error]
    SU5 -- Yes --> SU7[Frontend immediately calls POST /api/user/signin]
    SU7 --> SU8[AuthContext stores JWT in localStorage]
    SU8 --> SU9[Navigate to /events]
    SU9 --> SU10{Signed up user path}
    SU10 -->|Stay attendee| ATT0
    SU10 -->|Open Create tab and finish Stripe Connect later| ORG0
  end

  subgraph SigninFlow[Start 2: Sign In]
    SI0([Sign In]) --> SI1[Enter email and password]
    SI1 --> SI2{Credentials valid?}
    SI2 -- No --> SI3[Show login error]
    SI3 --> SI4[Optional Forgot Password]
    SI4 --> SI5[POST /api/user/forgot-password]
    SI5 --> SI6[Open reset link]
    SI6 --> SI7[POST /api/user/reset-password/:token]
    SI2 -- Yes --> SI8[Return JWT and user]
    SI8 --> SI9[AuthContext stores JWT in localStorage and navigates to /events]
    SI9 --> SI10{Role on signin}
    SI10 -->|Attendee| ATT0
    SI10 -->|Organizer| ORG0
    SI10 -->|Admin| ADM0
  end

  subgraph SharedAuth[Shared Auth and Profile]
    SA0[Later visits with persistLogin enabled] --> SA1[AuthProvider reads token from localStorage]
    SA1 --> SA2[GET /api/user/validate-token]
    SA2 --> SA3{Token valid?}
    SA3 -- Yes --> SA4[Restore user session]
    SA3 -- No --> SA5[Clear token and stay signed out]

    SH0[/events via PrivateRoute/]
    SH1[Top-right Hi first_name button]
    SH1 --> SH2[/profile via PrivateRoute/]
    SH2 --> SH3[Read only profile rows]
    SH3 --> SH4[Header pencil enters edit mode]
    SH4 --> SH5[PATCH /api/user/profile]
    SH2 --> SH6[Log out clears token and user state]
    SH2 --> SH7{Role 2 or 3?}
    SH7 -- Yes --> SH8[Show Billing card from GET /api/user/profile/dashboard]
    SH7 -- No --> SH9[Profile only]
    SH8 --> SH10{Admin role 3?}
    SH10 -- Yes --> SH11[Show Admin Tools scheduler status cards]
  end

  subgraph AttendeePath[Attendee Path]
    ATT0[Events page] --> ATT1{Checked in In Progress event exists?}
    ATT1 -- Yes --> ATT2[EventContext shows only that one active event]
    ATT1 -- No --> ATT3[Show normal event list with mock events hidden]
    ATT2 --> ATT4{Tab}
    ATT3 --> ATT4
    ATT4 -->|My| ATT5[Show registered waitlisted and created events]
    ATT4 -->|All| ATT6[Show all visible events]
    ATT4 -->|Create| ATT7[Show Stripe organizer setup card]

    ATT7 --> ATT8[POST /api/user/connect/onboarding]
    ATT8 --> ATT9[Return from Stripe then Check Setup]
    ATT9 --> ATT10[POST /api/user/organizer-status/refresh]
    ATT10 --> ORG0

    ATT5 --> ATT11{Any visible events?}
    ATT11 -- No --> ATT12[Show message to switch to All]
    ATT5 --> ATT13[Past Events accordion also available]
    ATT6 --> ATT13

    ATT6 --> ATT14{Event card state}
    ATT14 -->|Registration Open and not registered| ATT15[Sign Up button]
    ATT14 -->|Waitlisted| ATT16[Waitlisted chip and Leave Waitlist]
    ATT14 -->|Registered before event starts| ATT17[Registered chip and Cancel Registration]
    ATT14 -->|Checked In before event starts| ATT18[Checked In chip]
    ATT14 -->|In Progress with registration record| ATT19[Show timer card]
    ATT14 -->|In Progress without registration| ATT20[Read only card]
    ATT14 -->|Completed or older than 48h| ATT21[Past event card]

    ATT15 --> ATT22[Open confirm dialog]
    ATT22 --> ATT23{Paid event?}
    ATT23 -- No --> ATT24[POST /api/events/:id/register join_waitlist false]
    ATT24 --> ATT25{Registration outcome}
    ATT25 -- Success --> ATT26[Refresh events and show Registered]
    ATT25 -- Full or gender cap --> ATT27[Open waitlist dialog]
    ATT25 -- Other error --> ATT28[Show API error]

    ATT23 -- Yes --> ATT29[POST /api/events/:id/checkout]
    ATT29 --> ATT30{Checkout outcome}
    ATT30 -- Full or gender cap --> ATT27
    ATT30 -- Other error --> ATT28
    ATT30 -- Success --> ATT31[Redirect browser to Stripe Checkout]
    ATT31 --> ATT32[Stripe sends checkout.session.completed webhook]
    ATT32 --> ATT33[Upsert EventPayment row]
    ATT33 --> ATT34[Webhook calls register_for_event payment_confirmed true]
    ATT34 --> ATT35{Webhook registration outcome}
    ATT35 -- Success --> ATT36[Payment marked registered and attendee gets confirmation email]
    ATT35 -- Failure --> ATT37[Mark registration failure and try automatic full refund]
    ATT37 --> ATT38{Refund outcome}
    ATT38 -- Success --> ATT39[Registration failed refunded]
    ATT38 -- Failure --> ATT40[Refund failed state saved for support follow up]

    ATT27 --> ATT41{Join waitlist?}
    ATT41 -- Yes --> ATT42[POST /api/events/:id/register join_waitlist true]
    ATT42 --> ATT43[Show Waitlisted state after refresh]
    ATT41 -- No --> ATT44[Stay unregistered]

    ATT16 --> ATT45[POST /api/events/:id/cancel-registration]
    ATT45 --> ATT46[Removed from waitlist]

    ATT17 --> ATT47[Open cancel dialog]
    ATT47 --> ATT48{Paid event?}
    ATT48 -- Yes --> ATT49[Warn no refund through app]
    ATT48 -- No --> ATT50[Cancel directly]
    ATT49 --> ATT51[POST /api/events/:id/cancel-registration]
    ATT50 --> ATT51
    ATT51 --> ATT52[Refresh events]

    ATT43 --> ATT53{Spot opens later?}
    ATT53 -- Yes --> ATT54[Backend emails eligible waitlisted users to come back and sign up]
    ATT53 -- No --> ATT55[Stay waitlisted]

    ATT19 --> ATT56{Viewer type}
    ATT56 -->|Registered or checked in attendee| ATT57[Show attendee timer card]
    ATT56 -->|Manager viewing same card| ORG41
    ATT57 --> ATT58{Timer state}
    ATT58 -->|Inactive| ATT59[Event will be starting shortly]
    ATT58 -->|Active| ATT60[Show round countdown]
    ATT58 -->|Paused| ATT61[Show paused countdown]
    ATT58 -->|Break time| ATT62[Show next round countdown]
    ATT58 -->|Ended| ATT63[Show Event Finished Save your selections]

    ATT18 --> ATT64[My Schedule accordion available]
    ATT19 --> ATT64
    ATT64 --> ATT65{Expand while event is In Progress or Completed?}
    ATT65 -- No --> ATT66[Keep accordion closed]
    ATT65 -- Yes --> ATT67[GET /api/events/:id/schedule once]
    ATT67 --> ATT68{Schedule returned?}
    ATT68 -- No --> ATT69[Show waiting for schedule message]
    ATT68 -- Yes --> ATT70{Event status}
    ATT70 -- In Progress --> ATT71[Render each round with partner or Break Round]
    ATT71 --> ATT72[Tap Yes or No]
    ATT72 --> ATT73[Persist choices in localStorage]
    ATT73 --> ATT74[Save Selections]
    ATT74 --> ATT75[POST /api/events/:id/submit-selections]
    ATT75 --> ATT76{User checked in and event still In Progress?}
    ATT76 -- Yes --> ATT77[Selections saved to EventSpeedDate]
    ATT76 -- No --> ATT78[Show API error]

    ATT70 -- Completed --> ATT79[Hide Yes No buttons and hide break-only rows]
    ATT79 --> ATT80[Show partner name as card title]
    ATT80 --> ATT81{Mutual match?}
    ATT81 -- Yes --> ATT82[Show match message and copyable partner email]
    ATT81 -- No --> ATT83[Show not a match message]

    ATT0 --> SH1
  end

  subgraph OrganizerPath[Organizer Path]
    ORG0[Organizer on /events] --> ORG1{Create tab}
    ORG1 --> ORG2{Stripe Connect complete?}
    ORG2 -- No --> ORG3[Show setup card with Continue to Stripe and Check Setup]
    ORG3 --> ORG4[POST /api/user/connect/onboarding]
    ORG4 --> ORG5[Return from Stripe]
    ORG5 --> ORG6[POST /api/user/organizer-status/refresh]
    ORG6 --> ORG2
    ORG2 -- Yes --> ORG7[Show Create Event form]
    ORG7 --> ORG8[Enter name description local start datetime address capacity price and 60 40 toggle]
    ORG8 --> ORG9[Price floor enforced by intro or standard fee schedule]
    ORG9 --> ORG10[POST /api/events/create]

    ORG0 --> ORG11[My or All tabs show only events they created as manageable]
    ORG11 --> ORG12[Expand Event Controls]
    ORG12 --> ORG13[View Registered Users dialog]
    ORG13 --> ORG14[GET /api/events/:id/attendees]
    ORG14 --> ORG15[Search by first or last name prefix]
    ORG14 --> ORG16[Edit first name last name email gender church]
    ORG14 --> ORG17[Manual check in attendee]
    ORG14 --> ORG18[Export registered users CSV]

    ORG12 --> ORG19[View Waitlist dialog]
    ORG19 --> ORG20[GET /api/events/:id/waitlist]
    ORG20 --> ORG21[Search by first name last name or email prefix]
    ORG20 --> ORG22[Export waitlist CSV]

    ORG12 --> ORG23[Edit Event dialog]
    ORG23 --> ORG24[Edit name description start datetime address capacity price 60 40 toggle and status]
    ORG24 --> ORG25[PUT /api/events/:id]

    ORG12 --> ORG26[Delete Event]
    ORG26 --> ORG27{Status In Progress or Completed?}
    ORG27 -- Yes --> ORG28[Delete button disabled and backend rejects delete]
    ORG27 -- No --> ORG29[DELETE /api/events/:id]

    ORG12 --> ORG30[Generate Schedules]
    ORG30 --> ORG31[Enter requested tables and rounds]
    ORG31 --> ORG32[POST /api/events/:id/generate/schedules]
    ORG32 --> ORG33{Generation succeeded?}
    ORG33 -- No --> ORG34[Show failure]
    ORG33 -- Yes --> ORG35[Delete old EventSpeedDate rows]
    ORG35 --> ORG36[Set event status to In Progress]
    ORG36 --> ORG37[Persist actual num_rounds and num_tables]
    ORG37 --> ORG38[Reset EventTimer row]

    ORG12 --> ORG39{Event status In Progress or Completed?}
    ORG39 -- Yes --> ORG40[View All Schedules dialog]
    ORG40 --> ORG401[GET /api/events/:id/all-schedules]
    ORG401 --> ORG402[Search by attendee name prefix]
    ORG401 --> ORG403[No organizer CSV export button in current UI]
    ORG401 --> ORG404[Save Selections button stays disabled because no UI writes to that local state]

    ORG36 --> ORG41[In progress card shows manager timer panel]
    ORG41 --> ORG42{Timer state}
    ORG42 -->|Inactive| ORG43[Play starts current round]
    ORG42 -->|Active| ORG44[Back restarts or goes to previous round Pause pauses Forward ends round into break]
    ORG42 -->|Paused| ORG45[Play resumes]
    ORG42 -->|Break time| ORG46[Play advances to next round Back restarts current round]
    ORG42 -->|Ended| ORG47[Show Event Finished]
    ORG41 --> ORG48{Active or paused?}
    ORG48 -- No --> ORG49[Settings dialog can change round and break durations]

    ORG11 --> ORG50[Organizer can also sign up for events as an attendee]
    ORG0 --> SH1
  end

  subgraph AdminPath[Admin Path]
    ADM0[Admin on /events] --> ADM1[Create tab opens Create Event form immediately]
    ADM1 --> ADM2[POST /api/events/create]

    ADM0 --> ADM3[Admins can see mock events and manage any event]
    ADM3 --> ADM4[Expand Event Controls]
    ADM4 --> ADM5[View Registered Users dialog]
    ADM5 --> ADM6[Search edit manual check in and export registered users CSV]

    ADM4 --> ADM7[View Waitlist dialog]
    ADM7 --> ADM8[Search and export waitlist CSV]

    ADM4 --> ADM9[Edit Event dialog]
    ADM9 --> ADM10[PUT /api/events/:id]

    ADM4 --> ADM11[Generate Schedules for Registration Open event]
    ADM11 --> ORG31

    ADM4 --> ADM12[Delete Event]
    ADM12 --> ADM13{Status In Progress or Completed?}
    ADM13 -- Yes --> ADM14[Delete disabled in UI and blocked in backend]
    ADM13 -- No --> ADM15[DELETE /api/events/:id]

    ADM0 --> ADM16[In progress card always shows manager timer panel]
    ADM16 --> ORG42

    ADM0 --> ADM17[View All Schedules dialog]
    ADM17 --> ADM18[GET /api/events/:id/all-schedules]
    ADM18 --> ADM19[Search by attendee name prefix]
    ADM18 --> ADM20[Admin only Export CSV button]
    ADM18 --> ADM21[Disabled Save Selections button also exists here]

    ADM0 --> ADM22[No match visibility flow for managers]
    ADM22 --> ADM23[GET /api/events/:id/all-matches always returns 403]
    ADM0 --> SH1
  end

  subgraph MaintenanceFlow[Background Maintenance]
    MT0([App process import path]) --> MT1[start.py and wsgi.py both call start_embedded_scheduler]
    MT1 --> MT2{ENABLE_EMBEDDED_SCHEDULER truthy and not test parent process?}
    MT2 -- No --> MT3[No embedded scheduler thread]
    MT2 -- Yes --> MT4[Start BackgroundScheduler in America/New_York]
    MT4 --> MT5[9:00 AM Eastern auto complete job]
    MT4 --> MT6[9:00 PM Eastern reminder job]

    MT5 --> MT7[Try Postgres advisory lock 90412025]
    MT7 --> MT8{Lock acquired?}
    MT8 -- No --> MT9[Skip run]
    MT8 -- Yes --> MT10[Find In Progress events]
    MT10 --> MT11{Event Eastern start date before current Eastern date?}
    MT11 -- Yes --> MT12[Set event status to Completed]
    MT11 -- No --> MT13[Leave event unchanged]
    MT12 --> MT14[Record scheduler_job_runs success or failure]

    MT6 --> MT15[Try Postgres advisory lock 90412026]
    MT15 --> MT16{Lock acquired?}
    MT16 -- No --> MT17[Skip run]
    MT16 -- Yes --> MT18[Find registered or checked in attendees on future Registration Open events]
    MT18 --> MT19{Event is exactly 1 day 1 week or 1 month away in Eastern date?}
    MT19 -- Yes --> MT20[Send reminder email]
    MT19 -- No --> MT21[Skip attendee]
    MT20 --> MT22[Record scheduler_job_runs success or failure]

    MT23[GET /api/user/health] --> MT24[Check database connectivity and latest auto-complete run]
  end
```

## Matching Algorithm Flow

```mermaid
flowchart TD
  MA0([Generate schedule request]) --> MA1[Delete existing EventSpeedDate rows for this event]
  MA1 --> MA2[Load checked in attendees only]
  MA2 --> MA3{At least 2 attendees?}
  MA3 -- No --> MA4[Return -1 -1]
  MA3 -- Yes --> MA5[Split into males and females]
  MA5 --> MA6[Set adjusted tables to min requested tables and smaller gender count]
  MA6 --> MA7{At least 1 male and 1 female?}
  MA7 -- No --> MA4
  MA7 -- Yes --> MA8[Initialize all_compatible_dates and id_to_user]

  MA8 --> MA9[For each attendee in males plus females]
  MA9 --> MA10[Choose opposite gender pool]
  MA10 --> MA11[Query all historical EventSpeedDate rows involving this attendee]
  MA11 --> MA12[Build previous_date_user_ids]
  MA12 --> MA13[Initial compatible list<br/>different church unless one side has no church<br/>age diff at most 3<br/>never speed dated before]
  MA13 --> MA14[Compute min_dates_needed from tables rounds and same gender count]
  MA14 --> MA15{Enough compatible dates?}
  MA15 -- Yes --> MA20[Store compatible dates]
  MA15 -- No --> MA16[Retry with same church rule still enforced and age diff at most 4]
  MA16 --> MA17{Enough now?}
  MA17 -- Yes --> MA20
  MA17 -- No --> MA18[Retry with same church rule still enforced and age diff at most 5]
  MA18 --> MA19{Enough now?}
  MA19 -- Yes --> MA20
  MA19 -- No --> MA191[Final fallback allow same church keep age diff at most 5 still exclude previous speed dates]
  MA191 --> MA20
  MA20 --> MA21{More attendees left?}
  MA21 -- Yes --> MA9
  MA21 -- No --> MA22[Initialize rounds_completed_per_attendee to 0]

  MA22 --> MA23[For round 1 through requested rounds]
  MA23 --> MA24[Sort attendee ids by fewest rounds completed then fewest compatible dates]
  MA24 --> MA25[Reset seated attendees for this round]
  MA25 --> MA26[Reset available tables 1 through adjusted tables]
  MA26 --> MA27[For each sorted attendee]
  MA27 --> MA28{Already seated this round?}
  MA28 -- Yes --> MA27
  MA28 -- No --> MA29[Sort this attendee compatible dates by fewest rounds completed then smallest age difference]
  MA29 --> MA30[Scan for first compatible partner not seated this round]
  MA30 --> MA31{Found partner?}
  MA31 -- No --> MA32[Attendee sits out this round]
  MA31 -- Yes --> MA33[Set male_id and female_id from genders]
  MA33 --> MA34{Reusable previous round table for either participant still open?}
  MA34 -- Yes --> MA35[Reuse that table]
  MA34 -- No --> MA36[Take first available table]
  MA35 --> MA37[Create EventSpeedDate in memory]
  MA36 --> MA37
  MA37 --> MA38[Mark both attendees seated and increment both round counters]
  MA38 --> MA39[Remove each other from both compatible lists so pair cannot repeat in this event]
  MA39 --> MA40{Any tables left this round?}
  MA40 -- No --> MA41[End this round early]
  MA40 -- Yes --> MA27
  MA32 --> MA40
  MA41 --> MA42{More rounds requested?}
  MA42 -- Yes --> MA23
  MA42 -- No --> MA43[Persist all EventSpeedDate rows]
  MA43 --> MA44{Rows persisted and max round available?}
  MA44 -- No --> MA4
  MA44 -- Yes --> MA45[Return actual max round used and adjusted table count]
```
