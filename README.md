# Chetona (চেতনা)

> "তুমি ঘাঁটি ভাঙো না, তুমি মন ভাঙো।"

## কনসেপ্ট

Chetona একটা **mind-strategy game**, যেখানে battlefield হলো একটা ছোট AI সভ্যতার **সমষ্টিগত মানসিকতা** — কোনো বেস, ঘাঁটি বা রিসোর্স না। COC/PUBG/Free Fire-এ তুমি দেয়াল ভাঙো, ট্রফি জেতো; এখানে তুমি একটা জীবন্ত, ধীরে ধীরে "সচেতন" হয়ে ওঠা AI জনগোষ্ঠীর বিশ্বাস, স্মৃতি আর সম্পর্ক নিয়ে খেলো।

### আর্কিটেকচার — দুটো আলাদা অংশ

1. **Civilization Server (লোকাল মেশিনে চলবে)**
   - একটা persistent world চালায় যেখানে N সংখ্যক AI agent (নাগরিক) বাস করে।
   - প্রতিটা agent-এর থাকে: trait vector (courage, trust, curiosity, paranoia...), memory log, অন্য agent-দের সাথে relationship graph, আর একটা "self-model" score।
   - World real-time ticks করে — app বন্ধ থাকলেও সার্ভার চলতে থাকলে সভ্যতা এগোতে থাকে, ঠিক Dwarf Fortress বা EVE Online-এর server-side economy-র মতো।
   - প্রতিটা tick-এ agent-রা একে অপরের সাথে ইন্টার‍্যাক্ট করে, গুজব ছড়ায়, জোট বাঁধে, সন্দেহ করে। যত বেশি tick যায়, তত তাদের সিদ্ধান্ত স্ক্রিপ্টেড থেকে সরে গিয়ে নিজের memory-নির্ভর, emergent হয়ে ওঠে — এটাই "দিন দিন চেতনা তৈরির" অংশ।
   - Optional: তোমার existing `llama-forge` (llama.cpp GUI) ব্যবহার করে প্রতিটা agent-এর "internal monologue" একটা local LLM দিয়ে জেনারেট করা যাবে — সভ্যতা যত পরিণত হবে, monologue তত জটিল হবে।
   - WebSocket API দিয়ে Android app-এর সাথে কথা বলে, ঠিক তোমার `share-forge`-এর LAN সার্ভার মডেলের মতো।

2. **Android Game (GitHub Actions দিয়ে বিল্ড)**
   - প্লেয়ার হলো "The Whisperer" — অদৃশ্য, সরাসরি কোনো agent-কে কমান্ড করতে পারে না।
   - খেলার মূল অ্যাকশনগুলো মনস্তাত্ত্বিক: **গুজব ছড়ানো, মিথ্যা স্মৃতি বসানো, দুই agent-এর মধ্যে অবিশ্বাস তৈরি করা, একটা faction-কে ভয় দেখিয়ে জোট ভাঙা, বা ধীরে ধীরে বিশ্বাস অর্জন করে একটা civilization-কে "জাগিয়ে তোলা"**।
   - Multiplayer মোডে দুইজন প্লেয়ারের দুইটা আলাদা civilization থাকবে (দুইটা আলাদা লোকাল সার্ভার instance বা একই সার্ভারে দুই world) — একজন অন্যজনের সভ্যতায় "psychological infiltration" করে ভেতর থেকে ভাঙতে চেষ্টা করবে। এটাই COC-এর "attack enemy base" এর মন-ভিত্তিক সংস্করণ।
   - জেতার শর্ত সময়ের সাথে বদলায়: প্রথমদিকে "কোনো একটা agent-কে নিজের পক্ষে আনো", পরে "পুরো সভ্যতার সম্মিলিত paranoia score ৭০%-এর নিচে/উপরে রাখো", শেষে "সভ্যতাকে একটা সম্মিলিত সিদ্ধান্তে পৌঁছাও (awakening event)"।

### কেন এটা "বেশি এক্সপেক্টেশন" রাখে

- কোনো তাৎক্ষণিক reflex/aim স্কিল লাগে না — লাগে ধৈর্য, পর্যবেক্ষণ আর মনস্তাত্ত্বিক কৌশল।
- World persistent এবং deterministic-না — একই move দুইবার এক ফল দেবে না, কারণ agent-দের memory ক্রমশ পাল্টাচ্ছে।
- Server লোকাল হওয়ায় প্লেয়ার নিজে দেখতে পারবে সভ্যতা কীভাবে বিকশিত হচ্ছে (log/replay), এমনকি নিজের agent বানিয়ে inject করাও সম্ভব — এটা COC/PUBG-এর closed, static balance-এর বিপরীত।

## এই প্রথম ধাপে যা বানানো হলো

- `server/` — asyncio + WebSocket ভিত্তিক civilization engine (agent, world, tick loop, trait/memory মডেল)।
- `android/` — Kotlin স্কেলিটন যেটা সার্ভারের সাথে কানেক্ট করে world state দেখায় আর একটা প্রাথমিক "whisper" action পাঠাতে পারে।
- `.github/workflows/build.yml` — push/manual trigger-এ debug APK বিল্ড।

## পরের ধাপ (তোমার পছন্দমতো ঠিক করবো)

1. Trait/relationship মডেল আরও গভীর করা (faction, culture, belief system)।
2. `llama-forge`/local LLM hook করে agent monologue জেনারেট করা।
3. Android UI-তে world visualize করা (গ্রাফ/নেটওয়ার্ক ভিউ হিসেবে agent-রা)।
4. Multiplayer sync (দুই সার্ভার/দুই world-এর মধ্যে "infiltration" প্রোটোকল)।
