# Angels-TV-Animator v0.9.0

> ⚠️ **This project is still in development and not production-ready.**
> 
> 🔒 **Security Notice:** This application is designed for **local network use only**. Do NOT expose it to the public internet. See Security Notice section below for details.

A lightweight **Flask-SocketIO** server that displays HTML/CSS/JS animations or videos on a Smart TV — with real-time updates triggered via **OBS WebSocket**, **StreamerBot**, or **REST API**.  
Upload and manage media entirely through the web-based admin panel, no manual file edits required.

---

## ✨ Features

- 🎨 Serve HTML/CSS/JS or video animations to Smart TVs
- ⚡ Real-time switching via WebSocket or REST
- 🖥️ Web-based Admin UI for managing media, users, and triggers
- 🎮 OBS & StreamerBot integration for event-driven control
- 🔇 Videos are muted by default (Chrome autoplay compliant)
- 🐳 Simple one-command Docker deployment

---

## � Preview

### Admin Dashboard Interface
![Admin Dashboard](docs/images/Screenshot%202026-02-25%151100.png)
*Web-based admin interface for managing animations, users, and real-time triggers*

### Live Animation Examples

#### HTML/CSS Animation
![HTML Animation Demo](docs/images/Recording%202025-10-23%20104808.gif)
*Real-time HTML/CSS animations with instant switching capabilities*

#### Video Animation
![Video Animation Demo](docs/images/Recording%202025-10-23%20104711.gif)
*Seamless video playback with WebSocket-triggered switching*

---

## �🚀 Installation (Docker)

### Prerequisites

You only need **one** of the following installed on your system:

- [Docker Desktop](https://docs.docker.com/get-started/get-docker/) *(recommended for Windows/macOS)*
- [Docker Engine](https://docs.docker.com/engine/install/) *(for Linux servers)*
- [Docker Compose](https://docs.docker.com/compose/install/) *(included with most Docker Desktop installs)*

> 🧩 **Note:** See the included [`docker-compose.yml`](./docker-compose.yml) for bind mounts and configuration details.

---

### Build & Run

> 🧱 **Docker Hub:** Prebuilt images are coming soon!  
> For now, during testing, please build manually.

1. **Clone this repository:**
   ```bash
   git clone https://github.com/angelicadvocate/Angels-TV-Animator.git
   cd Angels-TV-Animator
   ```

2. **Build and start the container:**
   ```bash
   docker compose up -d --build
   ```

   > 📡 **Port Note:** This application uses **internal Docker ports 8080 and 8081** by default:
   > - Port **8080**: Main web interface, admin panel, and Socket.IO  
   > - Port **8081**: Raw WebSocket for StreamerBot integration (always main port + 1)
   >
   > These ports are used throughout the documentation. If you remap them in `docker-compose.yml` (e.g., `9000:8080`), use your **external mapped ports** instead of the defaults shown in examples.

3. **Access the web interfaces:**
   - **Admin Panel:** http://[DOCKER_HOST_IP]:8080/admin
   - **TV Display:** http://[DOCKER_HOST_IP]:8080
   - **Health Check:** http://[DOCKER_HOST_IP]:8080/health *(JSON server status & diagnostics)*
   - **Socket.IO API:** ws://[DOCKER_HOST_IP]:8080/socket.io/ *(Flask-SocketIO on main port)*
   - **Raw WebSocket:** ws://[DOCKER_HOST_IP]:8081/ *(StreamerBot integration)*

   > 💡 **Remember:** If you remapped ports in docker-compose.yml, replace `8080` and `8081` with your custom ports.

### Default Login

- **Username:** `admin`
- **Password:** `admin123`

> ⚠️ **Change this immediately in the Admin → Users page after first login.**

### 🔒 Security Notice

**Angels-TV-Animator is designed for local network use only.** This application is intended to run on a trusted local network (LAN) and should **NOT** be exposed to the public internet without additional security measures.

**Important Security Considerations:**

- **Local Network Only**: Deploy this application on your local network only (e.g., `192.168.x.x`, `10.x.x.x`)
- **Do NOT expose ports to the internet**: Never forward ports 8080/8081 through your router to the internet
- **Firewall Protection**: Ensure your network firewall blocks external access to these ports
- **Password Security**: All passwords are now hashed using industry-standard PBKDF2-SHA256
- **Network Responsibility**: You are responsible for your network's security configuration
- **Trusted Devices Only**: Only connect trusted devices (your streaming PC, Smart TV, mobile devices) on the same network

**Best Practices:**
- Change default credentials immediately after first login
- Use strong, unique passwords for all user accounts
- Keep your Docker host and network router updated with security patches
- Use a dedicated VLAN for streaming equipment if possible
- Regularly review connected devices in the admin dashboard

> 💡 **Bottom Line**: Think of this like a smart home device — it's secure on your local network, but should never be accessible from the internet.

---

## 📚 Next Steps: Setup & Instructions

Once the container is running and you've logged into the admin panel:

1. Click the **"Setup/Instructions"** button on the admin dashboard
2. Review the **"Getting Started"** guide for detailed setup and usage instructions
3. Check out **OBS Integration**, **StreamerBot Setup**, and **Troubleshooting** sections

All configuration, integration guides, and best practices are available directly in the web UI.

---

## 🧭 Using the Admin Interface

All configuration and media management are now handled in the web UI:

- Upload or remove HTML and video animations
- Switch currently active media in real time
- Manage user accounts and credentials
- Trigger animations manually or link to OBS/StreamerBot events

> **No manual code edits required** — manage media directly from the Admin Interface.

---

## 🔗 Integrations

Angels-TV-Animator integrates seamlessly with event-based tools like OBS and StreamerBot:

- **OBS WebSocket:** Trigger media changes on scene transitions
- **StreamerBot:** Automate event-based triggers
- **REST API:** For simple or legacy integrations

### Example WebSocket Event

```json
{
  "event": "trigger_animation",
  "data": {
    "animation": "intro.html"
  }
}
```

---

## 📺 Smart TV Setup

1. **Find your Docker host IP** (e.g., `192.168.1.100`)

2. **Start the container:**
   ```bash
   docker compose up -d
   ```

3. **On your Smart TV browser, open:**
   ```
   http://192.168.1.100:8080
   ```

The current animation or video will auto-play fullscreen. Changes appear instantly when triggered via the admin UI, OBS, or StreamerBot.

---

## 🧠 Tips

- **Responsive Design:** Use `vw`, `vh`, and flexbox for Smart TV-friendly layouts
- **Performance:** Keep animations lightweight for older TV browsers
- **Testing:** Preview animations in a desktop browser before deploying
- **Muted Autoplay:** All videos are auto-muted to comply with Chrome autoplay restrictions

---

## 🧩 Developer Notes

- Built with **Flask-SocketIO + Docker** for lightweight, real-time media control  
- Internal Docker ports: **8080** (web interface, admin panel, socket.io) + **8081** (raw WebSocket for StreamerBot)
- Raw WebSocket port is automatically set to main port + 1
- All documentation assumes default internal ports; adjust accordingly if you remap ports in docker-compose.yml

---

## 📄 License

See [LICENSE](LICENSE) for details.
