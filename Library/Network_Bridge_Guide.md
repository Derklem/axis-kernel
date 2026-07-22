# Network Stabilization: The Bridge Protocol

**Problem:** "Double NAT" (Two Captains, One Ship).
**Symptoms:** Intermittent drops, "No Internet" (while lights are on), Tailscale/VPN confusion.

### How to Fix (The Bridge Mode)
This stops your ISP modem from trying to be a "Router" and makes it just a "Modem."

1.  **Log into ISP Modem:**
    -   Usually `192.168.0.1` (The "Hop 2" address we found).
    -   Type that IP into a browser.
    -   *Password:* Usually on a sticker on the device (unless you changed it).

2.  **Find "Bridge Mode":**
    -   Look for settings like: `Gateway Mode`, `NAT Mode`, or `Bridge Mode`.
    -   Switch it to **"Bridge"** (or Disable NAT).
    -   **Click Save/Apply.**

3.  **The Reset:**
    -   The Modem will reboot.
    -   **Important:** Your Wi-Fi from the *ISP Box* will turn off (this is good!).
    -   Your **Netgear** will now get the "Real" Internet connection.

### The Tailscale Factor
You mentioned **Tailscale**.
-   If you have "Use Exit Node" enabled, disable it for now.
-   If Double NAT exists, Tailscale fights hard to punch through it. Fixing the Bridge Mode often fixes Tailscale instability too.

*Status: Advisory Only. Proceed when ready.*
