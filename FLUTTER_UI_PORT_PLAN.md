# Relay — HTML → Flutter UI Port Plan

**For:** an implementing agent (or developer).
**Goal:** Port the confirmed HTML UI at `app-ui-html/relay-app.html` into clean Dart/Flutter widgets inside the existing `owner_app/` project, **pixel-faithfully**.

---

## 0. Read this first — non-negotiables

1. **The HTML is the single source of truth.** `app-ui-html/relay-app.html` is a **confirmed, final design**, not a suggestion. Do not "improve", re-space, re-color, restyle, add, or drop anything. Match it. Every number in this plan was extracted directly from that file — if this plan and the HTML ever disagree, the HTML wins, but they should not disagree.
2. **Demo only. Do NOT wire any real backend.** No Python client, no notification listener, no `http`, no LAN discovery, no permissions logic. The screen must run standalone on mock data.
3. **"No functionality" means no _backend_ functionality — not a dead screen.** The HTML's own client-side interactions (tab switching, chip/search filtering, opening the confirm sheet, confirm/reject mutating the mock list, toggles, toasts) **are part of the UI** and must be reproduced exactly, using in-memory `setState` only. Reproduce them; connect nothing to the outside world.
4. **Do NOT touch the backend or existing wired UI.** Leave every file in section 2's "hands-off" list exactly as is. The port lives in brand-new files under a new folder and its own entry point.

---

## 1. What we are building

A 4-screen mobile app shell that is a 1:1 visual + interaction clone of the HTML:

- **Home** — brand bar, "Total received today" hero, Pending payments section, Recent payments section.
- **Payments** — title, search field, status filter chips, grouped transaction list (Today / Yesterday).
- **Account** — profile card, Business menu group, Preferences menu group, Log out.
- **Settings** — reached from the gear icon (and from Account → "Notification access"); status card + toggle groups.

Persistent chrome: a **bottom tab bar** (Home / Payments / Account). Settings is a pushed screen with a back button, not a tab.

Overlays: a **bottom sheet** ("Confirm payment"), its **scrim**, and a **toast**.

> **Skip the phone bezel.** The `.phone` frame (rounded 46px corners, `box-shadow` bezel, the `#e8e8ee` page backdrop) is only the web preview's mockup chrome. On device the app is full-screen. The Scaffold background is the screen background `--bg` `#FCFCFD`. Wrap content in `SafeArea`.

---

## 2. File layout & hands-off list

### Create these NEW files (nothing else touched)

```
owner_app/
  lib/
    demo_ui/
      demo_app.dart            # MaterialApp + theme (Manrope), home = DemoShell
      demo_shell.dart          # IndexedStack of 4 screens + bottom tab bar + settings push + overlays host
      tokens.dart              # RColors, RText, RSpace, RRadii, RShadow — all design tokens
      models.dart              # Payment model, PayStatus enum, seed data, formatters (money/initials)
      icons.dart               # exact SVG path strings from the HTML, as named constants
      screens/
        home_screen.dart
        payments_screen.dart
        account_screen.dart
        settings_screen.dart
      widgets/
        app_top_bar.dart       # brand logo + settings gear (the .appbar)
        section_card.dart      # white rounded card container (.card)
        payment_row.dart       # .row — home + payments variants
        avatar.dart            # initials / check / cross avatar
        filter_chips.dart      # .chips
        search_field.dart      # .search
        menu_item.dart         # .mi row (+ danger variant)
        pill_switch.dart       # .switch custom toggle
        confirm_sheet.dart     # .sheet bottom sheet
        toast.dart             # .toast
    main_demo.dart             # entry point: runApp(const DemoApp());
  assets/
    images/
      logo.png
      logo-full.png
    fonts/                     # only if bundling Manrope (see §4)
```

Run the demo with:
```
flutter run -t lib/main_demo.dart
```
This keeps the real app (`lib/main.dart` → `OperatorScreen`) and its backend intact. **Do not change `lib/main.dart`.** (When the team later decides the demo UI is the real UI, that's a one-line home swap — not part of this task.)

### HANDS-OFF — do not edit, import, or depend on these

- `lib/main.dart`
- `lib/api/python_client.dart`
- `lib/notification/notification_bridge.dart`
- `lib/ui/operator_screen.dart`
- `lib/ui/widgets/*` (access_status, credit_feed, dnd_status, lan_endpoint, match_banner, pending_list)
- everything under `backend/`, `android/` app logic, `context.md`, the PRD.

The demo folder must not import anything from `lib/api`, `lib/notification`, or `lib/ui`. Zero coupling.

---

## 3. Dependencies (pubspec.yaml)

Add to `dependencies:` (keep existing `http`, `cupertino_icons`):

```yaml
  flutter_svg: ^2.0.10        # render the HTML's exact SVG icons verbatim
  google_fonts: ^6.2.1        # Manrope — OR bundle it, see §4
```

> **Why `flutter_svg`:** the HTML uses custom Lucide-style stroke icons. Material `Icons` are *not* the same shapes; using them would break "exactly as is." Port each SVG's raw markup as a string and render with `SvgPicture.string(...)`. See §5 icons.

Run `flutter pub get` after editing pubspec.

---

## 4. Fonts & assets

### Font: Manrope (weights 400–800)

The HTML loads `Manrope:wght@400..800`. Two options — **prefer bundling** for offline demo reliability (a hackathon phone may have no network on first run, and `google_fonts` fetches on first use):

**Option A (recommended) — bundle the TTFs.** Download Manrope static weights 400/500/600/700/800, drop into `owner_app/assets/fonts/`, and declare:
```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/images/
  fonts:
    - family: Manrope
      fonts:
        - asset: assets/fonts/Manrope-Regular.ttf   # weight: 400
        - asset: assets/fonts/Manrope-Medium.ttf
          weight: 500
        - asset: assets/fonts/Manrope-SemiBold.ttf
          weight: 600
        - asset: assets/fonts/Manrope-Bold.ttf
          weight: 700
        - asset: assets/fonts/Manrope-ExtraBold.ttf
          weight: 800
```
Then set `fontFamily: 'Manrope'` in the theme.

**Option B — `google_fonts`.** Use `GoogleFonts.manrope(...)` / `GoogleFonts.manropeTextTheme()`. Simpler, but needs network on first launch. If you pick B, still add the `assets/images/` block.

> **Weight note:** CSS uses `650` in a few spots (chips, `.mi-title`, `.date-label`, `.mi-sub.ok`). Flutter `FontWeight` only has 100-step stops — map **650 → `FontWeight.w600`**. Map: 400→w400, 500→w500, 600→w600, 700→w700, 800→w800.

### Images

Copy `app-ui-html/images/logo.png` and `logo-full.png` → `owner_app/assets/images/`. Declare `assets/images/` (shown above).
- `logo-full.png` → brand mark in the top bar (`.brand-logo`, height **32**, width auto).
- `logo.png` → the faded hero watermark (see Home hero, §9.1).

---

## 5. Icons (port SVGs verbatim)

Put each icon's exact SVG markup from the HTML into `icons.dart` as a `const String`, rendered via `SvgPicture.string`. Preserve `stroke-width`, `stroke-linecap`, viewBox, and paths exactly. Colors: where the HTML uses `currentColor`, drive it with `SvgPicture.string(..., colorFilter: ColorFilter.mode(color, BlendMode.srcIn))`; where it hardcodes a stroke (e.g. `#0d0d12`, `#3ea96a`, `#e24747`, `#5ee08a`), keep that literal.

Icons to port (search the HTML for these):
- **Settings gear** (`.icon-btn` on Home/Payments/Account) — 21×21, stroke `#0d0d12`, width 1.9.
- **Back chevron** (Settings top bar) — 20×20, stroke `#0d0d12`, width 2.
- **Search** magnifier — 18×18, `currentColor`, width 2.1.
- **Filter** funnel — 18×18, `#0d0d12`, width 1.9.
- **Row check** (successful avatar) — 19×19, stroke `#3ea96a`, width 2.7.
- **Row cross** (failed avatar) — 17×17, stroke `#e24747`, width 2.6.
- **Chevron-right** (`.mi-chev`) — 18×18, `currentColor` `#c4c4cc`, width 2.
- **Menu-item icons** (6 distinct): UPI/bank, business-name/home, business-details/doc, device/phone, notifications/bell, notification-access/shield, help/question, about/info, log-out/arrow — all 18×18, `currentColor`, width 1.9. Each `.mi-icon` tints via its container (purple on `--purple-tint`; red on `--red-bg` for danger).
- **Tab bar icons** (3): Home (filled path, `fill` + `stroke` currentColor), Payments (receipt outline), Account (person outline) — 26×26.
- **Toast check** — 18×18, stroke `#5ee08a`, width 2.6.
- **Sheet:** no icon.

> Copy the SVG strings straight out of `relay-app.html`; do not redraw from memory.

---

## 6. Design tokens (`tokens.dart`)

All values are 1:1 CSS px → Flutter logical px. **Letter-spacing conversion:** CSS `letter-spacing` is in `em`; Flutter `letterSpacing` is in logical px. `px = em × fontSize`. Pre-computed values are given in the type table (§8).

### 6.1 Colors — `RColors`

| Token | Hex | Use |
|---|---|---|
| purple | `#6A24F4` | primary, badges, links, active states |
| purpleTint | `#ECE2FD` | avatar/menu-icon/chip-on backgrounds |
| ink | `#0D0D12` | primary text, dark icon strokes |
| muted | `#74747F` | hero label/sub |
| muted2 | `#8A8A95` | secondary text, times, subs |
| cardLine | `#F1F1F4` | card border |
| bg | `#FCFCFD` | screen background |
| green | `#3EA96A` | success text/check |
| greenBg | `#E9F6EE` | success avatar bg |
| red | `#E24747` | fail/danger text/cross |
| redBg | `#FDE8E8` | fail avatar / danger icon bg |
| search | `#F1F1F4` | search field bg (== cardLine) |
| cardBg | `#FFFFFF` | card surface |
| iconBtnBorder | `#E9E9EE` | icon button border |
| switchOff | `#DEDEE4` | switch track off / grabber |
| ghostBtnBg | `#F2F2F5` | sheet "Reject" button bg |
| ghostBtnText | `#1C1C22` | sheet "Reject" text |
| tabIdle | `#83838E` | inactive tab |
| tabBorder | `#EDEDF1` | tab bar top border |
| chevron | `#C4C4CC` | menu chevron |
| placeholder | `#9A9AA4` | search placeholder + search icon |
| toastBg | `#111119` | toast background |
| toastText | `#FFFFFF` | toast text |
| toastCheck | `#5EE08A` | toast check stroke |
| scrim | `rgba(12,12,20,0.42)` → `Color(0x6B0C0C14)` | sheet scrim |

### 6.2 Radii — `RRadii`
card **16**, icon button **11**, search **12**, chip **10**, menu-icon **10**, avatar/badge/switch/dot **999 (StadiumBorder / full circle)**, sheet top corners **26**, button **13**, toast **13**, profile-avatar **999**.

### 6.3 Shadows — `RShadow`
- **card:** `BoxShadow(color: Color(0x09121223) /* rgba(18,18,35,.035) */, blurRadius: 3, offset: Offset(0,1))`.
- **sheet:** `BoxShadow(color: Color(0x290C0C19) /* rgba(12,12,25,.16) */, blurRadius: 40, offset: Offset(0,-12))`.
- Toast has no shadow. Icon buttons have border, no shadow.

### 6.4 Spacing — `RSpace`
Screen padding: `EdgeInsets.fromLTRB(20, 18, 20, 24)` (`.screen` padding `18px 20px 24px`).
Other spacings appear inline in each component spec below — use them exactly, do not round to an 8pt grid.

---

## 7. Data model & mock data (`models.dart`)

```dart
enum PayStatus { pending, successful, failed }

class Payment {
  final String id;
  String name;
  int amount;
  PayStatus status;
  String group;      // 'today' | 'yesterday'
  String clock;      // e.g. '10:24 AM'
  String relative;   // e.g. '2 min ago'
  String? ref;       // UPI ref, pending rows only
  Payment({required this.id, required this.name, required this.amount,
           required this.status, required this.group, required this.clock,
           required this.relative, this.ref});
}
```

Seed list (order matters — matches HTML exactly):

| id | name | amount | status | group | clock | relative | ref |
|---|---|---|---|---|---|---|---|
| p1 | Rahul Sharma | 850 | pending | today | 10:24 AM | 2 min ago | random 12-digit |
| r1 | Karan Mehta | 1200 | successful | today | 09:48 AM | Just now | — |
| r2 | Ananya Verma | 450 | successful | today | 09:15 AM | 8 min ago | — |
| p2 | Ananya Verma | 1150 | pending | yesterday | 07:30 PM | 4 min ago | random 12-digit |
| r3 | Rohit Singh | 650 | successful | yesterday | 06:20 PM | 21 min ago | — |
| f1 | Neha Gupta | 800 | failed | yesterday | 05:45 PM | 34 min ago | — |

Globals: `total = 12450`, `count = 14`.

Helpers:
- `money(int n)` → `'₹' + n` grouped in **Indian** digit style (en-IN): `12450 → ₹12,450`. Implement en-IN grouping (last 3 digits, then groups of 2) or use `NumberFormat.decimalPattern('en_IN')` from `intl` (add `intl` if you use it; otherwise hand-roll — it's a small function).
- `initials(String name)` → first letter of each word, upper, max 2 chars (`Rahul Sharma → RS`).
- `ref()` → 12-digit string (`400000000000 + random`), used for pending rows' UPI reference.

Status → label map: `{pending:'Pending', successful:'Successful', failed:'Failed'}`.

---

## 8. Type styles (`RText`)

Every text style, extracted from CSS. `letterSpacing` pre-computed to px (em×size). Family Manrope. `height` is CSS `line-height` (unitless → Flutter `height` directly).

| Style | size | weight | color | letterSpacing | height | notes |
|---|---|---|---|---|---|---|
| pageTitle | 30 | w800 | ink | -1.35 | 1.0 | Payments title |
| pageTitleSettings | 22 | w800 | ink | -0.99 | 1.0 | Settings header (`-.045em`) |
| heroLabel | 15 | w500 | muted | -0.18 | 1.2 | |
| heroAmount | 41 | w800 | ink | -2.05 | 1.05 | tabular figures |
| heroSub | 16 | w500 | muted | -0.288 | 1.2 | |
| secH2 | 19 | w800 | ink | -0.76 | 1.2 | section heading |
| badge | 12.5 | w700 | #fff | 0 | 1.0 | |
| link | 16 | w700 | purple | -0.40 | — | "View all" |
| rowName | 17 | w600 | ink | -0.476 | 1.2 | |
| rowTime | 14 | w500 | muted2 | -0.21 | 1.2 | |
| rowValue | 17 | w600 | ink | -0.51 | — | tabular, nowrap |
| payStatus | 13 | w600 | status color | -0.26 | 1.2 | pending=purple, successful=green, failed=red |
| empty | 15 | w500 | muted2 | -0.225 | — | |
| searchInput | 15 | w500 | ink | -0.30 | — | placeholder color `placeholder` |
| chip | 14 | w600 | muted2 | -0.28 | — | on → purple text (weight stays w600; css 650) |
| dateLabel | 13 | w600 | muted2 | -0.13 | — | css 650 |
| groupLabel | 12.5 | w700 | muted2 | +0.5625 | — | UPPERCASE, `+.045em` |
| profileName | 18 | w700 | ink | -0.54 | 1.2 | |
| profileEmail | 14 | w500 | muted2 | -0.21 | — | |
| miTitle | 16 | w600 | ink | -0.448 | 1.2 | css 650 |
| miSub | 13 | w500 | muted2 | -0.195 | 1.25 | |
| miSubOk | 13 | w600 | green | -0.195 | 1.25 | ".ok" variant |
| statusTitle | 16 | w700 | ink | -0.48 | — | Settings "Listening…" |
| statusSub | 14 | w500 | #8A8A95 | -0.252 | — | |
| tab | 13 | w600 | tabIdle | -0.325 | — | active: w800, purple |
| sheetTitle | 21 | w800 | ink | -0.798 | — | |
| sheetSub | 14 | w500 | muted2 | -0.21 | 1.45 | |
| sheetBig | 38 | w800 | ink | -1.824 | — | tabular |
| kv | 15 | w500 | — | -0.27 | — | key=muted2, value=w700 ink |
| btn | 16 | w700 | — | -0.448 | — | primary=#fff, ghost=ghostBtnText |
| toast | 15 | w600 | #fff | -0.375 | — | |
| avatarInitials | 12.5 | w800 | purple | -0.125 | — | `.row .avatar`, `-.01em` |
| profileAvatar | 16 | w800 | purple | -0.32 | — | `-.02em` |

> Tabular figures: apply `fontFeatures: [FontFeature.tabularFigures()]` to heroAmount, rowValue, sheetBig.

---

## 9. Screen-by-screen build spec

General: each screen is a scrollable column (`ListView`/`SingleChildScrollView`) with screen padding `fromLTRB(20,18,20,24)`. `.card + .card` gap = **20** top margin between stacked cards.

### 9.1 Home (`home_screen.dart`)

1. **Top bar** (`AppTopBar`): row, `padding 6 0 18 0`, space-between. Left = `logo-full.png` height 32. Right = settings gear icon button (40×40, radius 11, border `iconBtnBorder`, white bg) → navigates to Settings.
2. **Hero card** (`.card.hero`): white card, padding `34 20`, `margin-bottom 20`, overflow hidden.
   - Foreground column (constrained to ~68% width via `max-width:68%`): label "Total received today" (heroLabel); amount `₹12,450` (heroAmount, gap 11 top/9 bottom); sub "`14` payments" (heroSub).
   - **Watermark:** `logo.png`, height 210, positioned right `-48`, vertically centered (`translateY(-46%)`), `opacity .14`, behind the text (`Stack`). Apply the fade mask `linear-gradient(115deg, transparent 8%, #000 46%, #000 100%)` via `ShaderMask` (BlendMode.dstIn, a `LinearGradient` from transparent→opaque along ~115°). `IgnorePointer`. Clip to the card's rounded rect.
3. **Pending payments card** (`.card.sec`, padding `0 16 8`):
   - Section head (`padding 18 0 4`, space-between): left = "Pending payments" (secH2) + purple badge showing pending count (`2`); right = "View all" link → Payments screen with filter=pending.
   - Rows: all `pending` payments as **home-variant rows** (see §10 PaymentRow). If none: empty text "Nothing waiting. New payments show up here." (empty style, padding `14 0 16`). Badge hidden when count 0.
4. **Recent payments card** (`.card.sec`): head "Recent payments" (no badge) + "View all" → Payments filter=successful. Rows: **first 3** `successful` payments as home-variant rows.

### 9.2 Payments (`payments_screen.dart`)

1. Top bar (same as Home).
2. **Title** "Payments" (pageTitle, `margin 0 0 16`).
3. **Search row** (`margin-bottom 14`, gap 10): search field (`SearchField`, flex, height 44, radius 12, bg `search`, padding `0 14`, gap 10 — magnifier icon `placeholder` color + `TextField` placeholder "Search transactions") + filter icon button (40×40, funnel icon). Filter button → shows toast "Use the tabs to filter by status" (it does not open a real filter).
4. **Chips** (`FilterChips`, `margin-bottom 16`, horizontally scrollable, gap 8): `All` (default on), `Pending`, `Successful`, `Failed`. On chip: bg `purpleTint`, text purple; padding `8 16`, radius 10.
5. **List card** (`.card.sec`) containing grouped payments:
   - Filter by selected chip status (all/pending/successful/failed) AND by search query (case-insensitive match on name).
   - Group into **Today** then **Yesterday** (only render a group with items). Each group: a date label ("Today"/"Yesterday", dateLabel style, padding `12 0 2`; first one padding-top 6) followed by its rows as **payments-variant rows**.
   - If no items after filtering: empty text "No payments here yet."

### 9.3 Account (`account_screen.dart`)

1. Top bar (same).
2. **Profile card** (`.card.profile`, padding `18 16 16`): row (gap 14) of profile avatar (52×52 circle, `purpleTint` bg, purple text "RS", profileAvatar style) + column (name "Rahul Sharma" profileName; email "rahul@shopstore.in" profileEmail, margin-top 4). Below (margin-top 16): purple link button "View profile ›" (link style, size 15).
3. **Group label** "Business" (groupLabel, margin `22 0 9`).
4. **Business card** — 4 `MenuItem` rows, each: menu-icon (36×36 radius 10, `purpleTint` bg, purple icon), title, optional sub, right chevron.
   - UPI ID / "shopstore@ibl"
   - Business name / "ShopStore"
   - Business details / "View and edit your business information"
   - Device name / "Rahul's Pixel"
5. **Group label** "Preferences".
6. **Preferences card** — 4 MenuItems:
   - Notifications / "Manage notification settings"
   - Notification access / sub "Enabled" (miSubOk green) — **tapping navigates to Settings**. This sub text mirrors the notification-access switch state (Enabled/Off) — see §11.
   - Help & support / "Get help and contact support"
   - About Relay / "Version 1.0.0"
7. **Log out card** (`margin-top 16`): one danger MenuItem — icon bg `redBg` + red icon, title "Log out" in red, no chevron, no sub. Tap → toast "Logged out".

### 9.4 Settings (`settings_screen.dart`)

Pushed screen (not a tab). Bottom tab bar still visible; the previously-active tab stays highlighted (`lastTab`). Back button returns to that tab.

1. **Top bar variant:** back chevron icon button (left) + centered title "Settings" (pageTitleSettings, 22px) + a 40px spacer (right) to balance. (`padding 6 0 18`.)
2. **Status card:** status row (padding `18 16`, gap 12): green dot (9×9 circle, `green`) + column [ "Listening for payments" (statusTitle) / "Rahul's Pixel, connected" (statusSub, margin-top 3) ].
3. **Group label** "Payments" + card with 3 rows (each a `.mi` layout but non-tappable, `cursor:default`), title left + `PillSwitch` right:
   - "Confirm payments automatically" — switch **off**.
   - "Notification access" — switch **on** (this is the switch that drives the Account "Enabled/Off" text).
   - "Sound on payment" — switch **on**.
4. **Group label** "App" + card with 1 row: title "Payment history" left, plain text "Export" right (miSub style, muted2).

---

## 10. Shared widgets — exact specs

### AppTopBar
Row, `padding fromLTRB(0,6,0,18)`, space-between. Props: `onSettings`. Left = `Image.asset('assets/images/logo-full.png', height:32)`. Right = `IconButton`-style square (40×40, radius 11, border 1 `iconBtnBorder`, bg white) with the gear SVG. Active/pressed: subtle scale (optional — the `:active{transform:scale(.95)}` polish; fine to skip for demo).

### SectionCard (`.card`)
`Container` bg white, border `Border.all(color: cardLine, width: 1)`, radius 16, boxShadow [card]. Padding provided by caller (hero/sec/profile differ). Use `ClipRRect` where children need clipping (hero watermark).

### PaymentRow (`.row`)  — two variants
Shared: horizontal, `padding 12 0`, gap 16, cross-axis center.
- **Avatar** (34×34): pending → circle `purpleTint`, initials (avatarInitials, purple); successful → circle `greenBg` + check SVG; failed → circle `redBg` + cross SVG.
- **Meta** (expanded): name (rowName) over secondary line (rowTime), gap 4.
  - Home variant secondary = `relative` ("2 min ago"). Payments variant secondary = `clock` ("10:24 AM").
- **End:**
  - Home variant: just the amount (rowValue).
  - Payments variant: column right-aligned — amount (rowValue) over status label (payStatus, colored by status), gap 4.
- **Tappable only when `status == pending`** → opens the confirm sheet. Non-pending rows are inert (no ripple).

### Avatar
As above; takes `PayStatus` + `name`.

### FilterChips
Horizontal scroll (`SingleChildScrollView` horizontal, `clipBehavior` none), gap 8. Each chip: `padding 8 16`, radius 10; selected → bg `purpleTint`, text purple, else transparent bg, text muted2. Chip text weight w600. Emits selected `PayStatus?` (null = All).

### SearchField
`Container` height 44, bg `search`, radius 12, padding `0 14`, row gap 10: magnifier SVG (`placeholder` color) + `TextField` (no border, searchInput style, placeholder "Search transactions" in `placeholder` color). Emits query string.

### MenuItem (`.mi`)
Row, `padding 14 16`, gap 14. Leading = menu-icon box (36×36, radius 10; default bg `purpleTint` + purple icon; danger bg `redBg` + red icon). Body (expanded): title (miTitle; danger → red) + optional sub (miSub, or miSubOk when green). Trailing = chevron SVG (`chevron` color) unless `showChevron:false`. Optional `trailing` override slot (used by Settings for `PillSwitch` / "Export" text). `onTap` optional.

### PillSwitch (`.switch`)
46×28 track, radius full. Off → track `switchOff`; on → track `purple`. Knob 22×22 white circle, `top/left 3`, shadow `0 1px 3px rgba(0,0,0,.2)`, translateX **18** when on. Animate 200ms. Stateful/controlled bool.

### ConfirmSheet (`.sheet`) + scrim — see §12.
### Toast (`.toast`) — see §12.

---

## 11. Interaction/state spec (all local `setState` — no I/O)

Hold app state at `DemoShell` (or a small `ChangeNotifier`), passed down. State: `payments` (mutable list), `total`, `count`, `currentTab` (home/payments/account), `showingSettings` (bool overlay/route), `lastTab`, `chipFilter`, `searchQuery`, `notifAccessOn` (bool, default true), plus other toggle bools, and transient `activePayment` for the sheet.

Behaviours to reproduce **exactly** (from the HTML JS):

1. **Tabs:** switching Home/Payments/Account swaps the visible screen; the tapped tab highlights. Use an `IndexedStack` so scroll positions persist per the HTML feel (or rebuild — either is fine visually). On entering a screen, HTML resets its scroll to top; matching that is optional.
2. **Settings navigation:** gear icon (any screen) and Account→"Notification access" open Settings. Settings is shown over/in place of the current screen; the tab bar stays, `lastTab` stays highlighted. Back → return to `lastTab`.
3. **"View all" links:** Home "Pending → View all" opens Payments with chip=Pending; "Recent → View all" opens Payments with chip=Successful.
4. **Chips + search:** filter the Payments list live; grouped Today/Yesterday; empty state when nothing matches.
5. **Pending row tap → ConfirmSheet** with that payment's amount, name, relative time, UPI ref.
6. **Sheet "Confirm payment":** set status→successful, `relative='Just now'`, `clock=`now (`hh:mm AM/PM` en-IN upper), `group='today'`; move that payment to the **front** of the list; `total += amount`; `count += 1`; close sheet; toast "Payment confirmed". Home pending list shrinks, recent list/hero update accordingly.
7. **Sheet "Reject":** set status→failed; close sheet; toast "Payment rejected". (HTML does not move/relabel further.)
8. **Filter icon button (Payments):** toast "Use the tabs to filter by status". (No real filter panel.)
9. **Switches (Settings):** toggle their bool. The **Notification access** switch also updates the Account screen's "Notification access" sub → "Enabled" (green, miSubOk) when on / "Off" (muted, plain miSub) when off. Other switches are cosmetic.
10. **Log out:** toast "Logged out". (No navigation.)
11. **Scrim tap / Android back while sheet open:** close the sheet.

None of this calls a backend. Confirm/reject only mutate the in-memory list.

---

## 12. Overlays

Host the sheet, scrim, and toast in a `Stack` at `DemoShell` level so they float above screens **and** the tab bar (toast sits at `bottom: 88`, i.e. above the tab bar; sheet + scrim cover the whole phone area including tab bar, matching `z-index 20/21` over the `.tabbar`).

### Scrim + ConfirmSheet
- **Scrim:** full-bleed `Color(0x6B0C0C14)`, `AnimatedOpacity` 260ms, tap closes.
- **Sheet:** bottom-anchored, bg white, top corners radius 26, `padding fromLTRB(20,12,20,26)`, shadow [sheet]. Slide up from off-screen (`AnimatedPositioned`/`SlideTransition`, ~340ms, ease `cubic-bezier(.2,.9,.25,1)`).
- Content, top→bottom:
  - Grabber: 38×4 rounded bar, `switchOff` color, centered, `margin 0 auto 18`.
  - Title "Confirm payment" (sheetTitle, `margin-bottom 5`).
  - Sub "Your phone detected this payment. Confirm it to release the order." (sheetSub, `margin-bottom 20`).
  - Big amount (sheetBig, `margin-bottom 16`).
  - 3 key/value rows (`.kv`, `padding 11 0`, space-between): "From" / name; "Detected" / relative; "UPI reference" / ref. Keys muted2 w500, values ink w700.
  - Actions row (`margin-top 22`, gap 10): **Reject** (ghost btn — bg `ghostBtnBg`, text `ghostBtnText`, flex `0 0 38%`) + **Confirm payment** (primary btn — bg purple, text white, flex 1). Both radius 13, `padding 16 0`, btn text style.

### Toast (`.toast`)
Positioned `left/right 20, bottom 88`. bg `toastBg`, radius 13, `padding 14 16`, row gap 10: check SVG (`toastCheck`) + message (toast style, white). `AnimatedOpacity`+slide 240ms; auto-dismiss after **2200ms** (Timer; cancel/reset if a new toast fires). Text varies per action.

---

## 13. Theme (`demo_app.dart`)

```dart
MaterialApp(
  debugShowCheckedModeBanner: false,
  theme: ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: RColors.bg,
    fontFamily: 'Manrope',              // or GoogleFonts.manropeTextTheme()
    colorScheme: ColorScheme.fromSeed(seedColor: RColors.purple, brightness: Brightness.light)
        .copyWith(primary: RColors.purple, surface: RColors.cardBg),
    splashFactory: NoSplash.splashFactory, // HTML rows use opacity/scale, not ripples
  ),
  home: const DemoShell(),
);
```
Light theme only (the HTML is light). Do not reuse the existing dark theme from `main.dart`.

---

## 14. Bottom tab bar (`.tabbar`)

`Container` bg white, top border 1px `tabBorder`, `padding 11 8 14`. Row of 3 equal-flex tabs. Each tab: column, gap 7, `padding 4 0`; icon 26×26 + label (tab style). Active tab: color purple, label weight w800; inactive: `tabIdle`, w600. Wrap in `SafeArea(top:false)` so it clears the gesture bar. The Home icon is a **filled** shape when its tab is the semantic home — but per HTML the icon fill/stroke doesn't change with selection; only color changes. Keep the three SVGs fixed; recolor by active state.

---

## 15. Acceptance criteria / fidelity checklist

Port is done when all are true:

- [ ] `flutter run -t lib/main_demo.dart` launches the demo; `flutter analyze` is clean; existing `lib/main.dart` app still builds unchanged.
- [ ] Colors, radii, paddings, font sizes, weights, and letter-spacings match §6/§8 exactly (spot-check against the HTML side-by-side).
- [ ] Manrope renders (bundled or google_fonts); numbers use tabular figures where specified.
- [ ] All four screens match the HTML: Home (hero + pending + recent), Payments (search + chips + grouped list), Account (profile + 2 groups + logout), Settings (status + 2 groups).
- [ ] Icons are the HTML's own SVGs (via flutter_svg), not Material substitutes.
- [ ] Hero watermark: `logo.png`, right-anchored, faded (opacity .14) with the diagonal gradient mask, behind the text.
- [ ] Avatars: initials (pending), green check (successful), red cross (failed) with correct tinted backgrounds.
- [ ] Bottom sheet, scrim, and toast look and animate like the HTML; confirm/reject mutate the mock list per §11.6–7; hero/badge/lists update live.
- [ ] Chips + search filter the list and group by Today/Yesterday; empty states show correct copy.
- [ ] Settings notification-access switch drives the Account "Enabled/Off" sub.
- [ ] No import of `lib/api`, `lib/notification`, or `lib/ui`; no network/permission/notification calls anywhere in `demo_ui/`.
- [ ] Every backend/hands-off file in §2 is byte-for-byte unchanged.

---

## 16. Explicit "do NOT" list

- Do NOT modify `lib/main.dart`, `lib/api/*`, `lib/notification/*`, `lib/ui/*`, `backend/*`, or Android backend logic.
- Do NOT connect the demo to Python, HTTP, LAN discovery, notification listeners, or Android permissions.
- Do NOT redesign, re-space, recolor, rename labels, reorder rows, or "modernize" anything. The HTML is confirmed.
- Do NOT substitute Material icons for the custom SVGs.
- Do NOT add packages beyond `flutter_svg` and (optionally) `google_fonts` / `intl` without a stated reason.
- Do NOT introduce state management packages (Provider/Riverpod/Bloc); `setState` / a small `ChangeNotifier` is enough for a demo.
```
