# Angels-TV-Animator TODO List

> All open/pending items for **Angels-TV-Animator** go here.
> Items are **not considered complete** until moved to `CHANGELOG.md` and marked ✨ *COMPLETED*.

### Entry Format

```
## Priority Level (Category)

- [ ] **Feature idea title**
  - Details and actionables

- [x] **Feature being worked on** — `github:Username`
  - Details and actionables
```

| Part | Description |
|------|-------------|
| `- [ ]` | Idea / not yet started |
| `- [x]` | Actively being worked on |
| **Title** | Short description of what needs to be done |
| `github:Username` | Who is working on it (add when marking in-progress) |

---

## Priority: Low (Code Organization & Cleanup)

- [ ] **Add Images & GIF Animations to Instructions Pages**
  - Create screenshots and GIF walkthroughs for Getting Started, StreamerBot, OBS, and Troubleshooting pages
  - Store images in `static/assets/` directory (already exists)
  - Topics to capture: admin dashboard overview, file management workflow, OBS connection setup, scene mapping configuration, StreamerBot action creation, mobile control interface
  - Use GIFs to demonstrate multi-step workflows (e.g., drag-and-drop upload, animation switching, OBS scene-to-animation mapping)
  - Add `<img>` tags to instruction templates with proper alt text and responsive sizing
  - **Priority**: Low — instructions are functional without visuals but would benefit from visual guides

## Priority: Low (Future Enhancements)

- [ ] **Personalized Animation Alerts (StreamerBot Payload Pass-Through)**
  - Accept additional data in trigger payloads from StreamerBot (username, profile image URL, donation amount, sub tier, raid viewer count, message text, etc.)
  - Pass payload data through SocketIO to the TV client alongside the animation trigger
  - Animation HTML files read and display the dynamic data (e.g., follower's profile picture, "Thanks [username]!", "$5.00 from [user]")
  - StreamerBot already exposes these variables in its actions — just need to include them in the HTTP/WebSocket payload
  - **Scope**: Extends the existing trigger pipeline — no architectural changes needed, just a `payload` field on the trigger event
  - **Impact**: Transforms generic animations into personalized streamer alerts that rival dedicated overlay tools
  - Retrofit-friendly — existing animations simply ignore the payload field until updated to read it
  - **Research needed**: Document which StreamerBot variables are available per event type (follow, donation, raid, sub, etc.)
  - **Priority**: Low — ship with static text animations first, add personalization as a post-release enhancement

- [ ] **Multi-Channel TV Support (Up to 4 Channels)**
  - Add channel-based routes so multiple TVs can display different animations simultaneously
  - Each TV points to a different URL: `/ch1`, `/ch2`, `/ch3`, `/ch4` (cap at 4 for performance)
  - Default `/` route continues to work as-is (backwards compatible, acts like ch1 or "all channels")
  - **OBS mapping expansion**: Scene mappings go from `scene → animation` to `scene → {ch1: anim, ch2: anim, ...}`
  - Each channel listens for its own SocketIO events (e.g., `trigger_ch1`, `trigger_ch2`) so animations fire independently
  - Admin UI needs a channel selector in the OBS scene mapping interface and trigger controls
  - Mobile control page could add channel tabs or a channel dropdown
  - **Note**: Mobile control interface will need a revisit — could be as simple as a popup/modal when tapping an animation that asks which channel to play it on
  - **Use cases**:
    - Streamers with multi-TV setups (retro TV wall, dual monitor display, etc.)
    - Venues/bars using digital signage across multiple screens
    - Churches, events, or lobbies with different content per display
  - **Implementation approach**: Likely a parameterized video player route (`/ch/<int:channel>`) reusing the existing template with a channel context variable
  - StreamerBot/HTTP trigger API would accept an optional `channel` parameter (defaults to all channels for backwards compatibility)
  - **Priority**: Low — post-release feature, but high impact for multi-display setups and opens up the digital signage market

- [ ] **Now Playing / Clock Animation (Angels-Now-Playing Integration)**
  - Create `now_playing.html` animation that displays a live clock and a "Now Playing" widget
  - Integrate with the separate **Angels-Now-Playing** project (custom OBS now-playing overlay)
  - The Now Playing widget would show current song/media info on the TV display
  - Clock component: fullscreen time + date display, ambient/screensaver style
  - Now Playing component: embed or SocketIO integration with Angels-Now-Playing data
  - Could use the same iframe-over-gradient pattern as donation/follower/goal pages, or a native SocketIO integration for tighter control
  - **Priority**: Low — depends on Angels-Now-Playing project reaching a stable state first
