# Chetona3D — Phase 1

এটা Chetona-এর real 3D client, **Godot 4.3+** দিয়ে বানানো। এই client
`server/` (Python)-এর সাথে একই WebSocket protocol দিয়ে কথা বলে যা
Android app ব্যবহার করে — সভ্যতার সব logic (agent, faction, objective)
সার্ভারেই থাকে, এই client শুধু সেটা 3D-তে দেখায়।

## চালানোর ধাপ (Windows PC-তে)

1. [Godot Engine 4.3 বা তার পরের version](https://godotengine.org/download) ডাউনলোড করো
   (Standard version, .NET/C# version লাগবে না — আমরা GDScript ব্যবহার করছি)
2. Godot খুলে **Import** → এই `godot/` ফোল্ডারের `project.godot` ফাইল সিলেক্ট করো
3. প্রজেক্ট খুললে উপরে **Run Project** (F5) চাপো
4. আগে থেকে (একই মেশিনে বা LAN-এ) `server/` চালু থাকতে হবে:
   ```
   cd server
   python main.py
   ```
5. Game window-এ URL বসাও (ডিফল্ট `ws://localhost:8765/?world=alice` — একই মেশিনে
   সার্ভার চালালে এটাই কাজ করবে), **Connect** চাপো
6. প্রতিটা agent একটা রঙিন capsule হিসেবে ভেসে উঠবে — faction অনুযায়ী রঙ,
   defect করা agent হালকা/অর্ধ-স্বচ্ছ হয়ে যাবে

## এই ধাপে যা আছে

- 3D ground, sky, আলো, ক্যামেরা
- WebSocket দিয়ে সার্ভারের snapshot পড়া
- প্রতিটা agent-কে capsule হিসেবে বৃত্তাকারে সাজানো, faction-ভিত্তিক রঙ
- Objective banner UI-তে দেখানো
- Citizen-রা নতুন position-এর দিকে smoothly glide করে (snap না করে)

## পরের ধাপ (এখনো বাকি)

- Player avatar + movement (WASD/touch), camera follow
- Territory zones (faction অনুযায়ী রঙিন মাটি), day-night cycle
- Weather (rain particle, fog)
- জন্ম/মৃত্যু visual event, conflict animation
- Whisper/incite action UI (এখন শুধু দেখা যায়, action নেওয়া যায় না)
- Android-এর মতো token-based auth + reconnect-backoff

## Export (APK/PC build)

Godot editor-এর **Project → Export** থেকে Android/Windows/Linux export
preset যোগ করে বিল্ড করা যাবে। GitHub Actions দিয়ে headless export করাও
সম্ভব (`godot --headless --export-release`), কিন্তু এটার জন্য
export template ডাউনলোড আর signing setup লাগবে — এটা পরের ধাপে করবো।
