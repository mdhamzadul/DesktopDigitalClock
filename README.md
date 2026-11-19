# 🕒 Desktop Digital Clock (by AsR)

A lightweight, modern, transparent floating digital clock widget for Windows desktop.

![Desktop Digital Clock](https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge&logo=windows)
![Python](https://img.shields.io/badge/Python-3.12-yellow?style=for-the-badge&logo=python)
![Version](https://img.shields.io/badge/Version-1.1.0-brightgreen?style=for-the-badge)

---

## ✨ Features (ফিচারসমূহ)

- 🪟 **Frameless & Transparent**: সুন্দর এবং কোনো বর্ডার বা উইন্ডো ফ্রেম ছাড়া ডেসকটপের উপর ভেসে থাকে।
- 🔄 **Resizable (বড়-ছোট করার সুবিধা)**: 
  - ঘড়ির নিচে ডান কোণায় থাকা `⤡` আইকন ধরে ড্র্যাগ করে বড় বা ছোট করুন।
  - মাউস স্ক্রোল হুইল (Mouse Wheel Scroll Up / Down) ঘুরিয়ে সাথে সাথে জুম ইন/আউট করুন।
  - `Ctrl + Plus (+)` ও `Ctrl + Minus (-)` শর্টকাট।
  - রাইট-ক্লিক মেনু থেকে প্রিসেট সাইজ (Mini, Small, Medium, Large, Extra Large) নির্বাচন করার সুবিধা।
- 💾 **Auto-Save Settings**: ঘড়ির সাইজ, ডিসপ্লে পজিশন, রঙ এবং ১২/২৪ ঘণ্টার ফরম্যাট স্বয়ংক্রিয়ভাবে সেভ থাকে। পরের বার ওপেন করলে ঠিক আগের মতোই চালু হবে।
- 🎨 **Custom Color**: রাইট-ক্লিক করে যেকোনো পছন্দমতো নিয়ন বা সাধারণ কালার বেছে নেওয়ার সুবিধা।
- 📌 **Always on Top**: অন্যান্য উইন্ডোর ওপরে সবসময় দৃশ্যমান রাখার অপশন।
- ⏱️ **12h / 24h Toggle**: ১২ ঘণ্টা (AM/PM) বা ২৪ ঘণ্টার আন্তর্জাতিক ফরম্যাট টগল করার সুবিধা।
- 📦 **One-Click Installer**: ইন্সটলারের মাধ্যমে ডেস্কটপ ও স্টার্ট মেনু শর্টকাট এবং উইন্ডোজ স্টার্টআপে অটো-রান করার সুবিধা।

---

## 📥 Download (ডাউনলোড লিংক)

সরাসরি ব্যবহার করার জন্য কোনো পাইথন ইন্সটল করার প্রয়োজন নেই:
1. ডানপাশের **[Releases](https://github.com/)** সেকশনে যান।
2. **`Setup_DesktopDigitalClock_AsR.exe`** (ইন্সটলার) অথবা **`DesktopDigitalClock_AsR.exe`** (পোর্টেবল) ডাউনলোড করুন।
3. ডাবল ক্লিক করে ইনস্টল বা ওপেন করলেই চলবে!

---

## 🛠️ How to Run from Source (সোর্স কোড থেকে চালানো)

Python ইনস্টল থাকলে সরাসরি কমান্ড প্রম্পট বা পাওয়ারশেল থেকে রান করতে পারবেন:

```bash
# Clone the repository
git clone https://github.com/<your-username>/DesktopDigitalClock.git

# Go to directory
cd DesktopDigitalClock

# Run the clock
python desktop_clock.py
```

### Build .EXE (এক্সিকিউটেবল ফাইল তৈরি)
```bash
pyinstaller --clean --onefile --noconsole --name DesktopDigitalClock_AsR desktop_clock.py
pyinstaller --clean --onefile --noconsole --name Setup_DesktopDigitalClock_AsR --add-data "DesktopDigitalClock_AsR.exe;." installer.py
```

---

## 📜 License
Developed & Signed by **AsR**. Free for personal use.
