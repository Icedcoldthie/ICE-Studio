const config = window.ICE_CONFIG || {};

const $ = (id) => document.getElementById(id);

document.querySelectorAll(".nav").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav").forEach(x => x.classList.remove("active"));
        document.querySelectorAll(".page").forEach(x => x.classList.remove("active"));
        btn.classList.add("active");
        $("page-" + btn.dataset.page).classList.add("active");
        if (btn.dataset.page === "learning") loadHistory();
        if (btn.dataset.page === "knowledge") loadKnowledge();
    });
});

async function refreshStatus() {
    const data = await fetch("/api/status").then(r => r.json());
    $("ollamaStatus").textContent = data.ollama ? "Online" : "Offline";
    $("ollamaStatus").className = data.ollama ? "good" : "bad";
    $("streamerbotStatus").textContent = data.streamerbot ? "Verbonden" : "Niet verbonden";
    $("streamerbotStatus").className = data.streamerbot ? "good" : "bad";
    $("modelStatus").textContent = data.model;
    $("outfitStatus").textContent = data.outfit;
    $("statInteractions").textContent = data.stats.interactions;
    $("statViewers").textContent = data.stats.viewers;
    $("statApproved").textContent = data.stats.approved;
}

function addMessage(type, name, text, sources = []) {
    const box = document.createElement("div");
    box.className = "message " + type;
    box.innerHTML = `<strong>${escapeHtml(name)}</strong><div>${escapeHtml(text)}</div>` +
        (sources.length ? `<small>Bronnen: ${sources.map(escapeHtml).join(", ")}</small>` : "");
    $("chatWindow").prepend(box);
}

$("sendChat").addEventListener("click", async () => {
    const username = $("chatUsername").value.trim();
    const message = $("chatMessage").value.trim();
    if (!username || !message) return;

    addMessage("user", username, message);
    $("sendChat").disabled = true;
    $("sendChat").textContent = "ICE denkt…";

    const form = new FormData();
    form.append("username", username);
    form.append("message", message);
    const data = await fetch("/api/chat", {method: "POST", body: form}).then(r => r.json());

    addMessage("ice", "ICE", data.answer, data.sources || []);
    $("chatMessage").value = "";
    $("sendChat").disabled = false;
    $("sendChat").textContent = "Stuur naar ICE";
    refreshStatus();
});

$("chatMessage").addEventListener("keydown", e => {
    if (e.key === "Enter") $("sendChat").click();
});

$("savePersonality").addEventListener("click", async () => {
    const payload = {
        response_style: $("responseStyle").value,
        reply_mode: $("replyMode").value,
        personality: {
            humor: Number($("humor").value),
            sarcasm: Number($("sarcasm").value),
            energy: Number($("energy").value),
            friendly: Number($("friendly").value)
        }
    };
    await fetch("/api/settings", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
    alert("Persoonlijkheid opgeslagen.");
});

$("addKnowledge").addEventListener("click", async () => {
    const form = new FormData();
    form.append("title", $("knowledgeTitle").value);
    form.append("category", $("knowledgeCategory").value);
    form.append("content", $("knowledgeContent").value);
    form.append("source", $("knowledgeSource").value);
    await fetch("/api/knowledge", {method: "POST", body: form});
    $("knowledgeTitle").value = "";
    $("knowledgeContent").value = "";
    loadKnowledge();
});

$("knowledgeSearch").addEventListener("input", loadKnowledge);

async function loadKnowledge() {
    const query = encodeURIComponent($("knowledgeSearch").value || "");
    const data = await fetch("/api/knowledge?query=" + query).then(r => r.json());
    $("knowledgeResults").innerHTML = data.items.map(item => `
        <div class="history-card">
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.category)} · ${escapeHtml(item.source)}</small>
            <p>${escapeHtml(item.content)}</p>
        </div>
    `).join("") || "<p>Geen resultaten.</p>";
}

$("searchGames").addEventListener("click", async () => {
    const query = encodeURIComponent($("gameQuery").value.trim());
    const data = await fetch("/api/games/search?query=" + query).then(r => r.json());
    $("gameResults").innerHTML = data.items.map(item => `
        <article class="game-card">
            ${item.image ? `<img src="${item.image}" alt="">` : ""}
            <div>
                <strong>${escapeHtml(item.name || "Onbekend")}</strong>
                <p>${escapeHtml(item.price || item.error || "")}</p>
                <small>${escapeHtml(item.source || "")}</small>
            </div>
        </article>
    `).join("") || "<p>Geen games gevonden.</p>";
});

async function loadHistory() {
    const data = await fetch("/api/history?limit=40").then(r => r.json());
    $("historyList").innerHTML = data.items.map(item => `
        <article class="history-card">
            <strong>${escapeHtml(item.username)}</strong>
            <p>${escapeHtml(item.message)}</p>
            <p><b>ICE:</b> ${escapeHtml(item.answer)}</p>
            <small>${escapeHtml(item.created_at)} · ${escapeHtml(item.knowledge_used || "Geen bron geregistreerd")}</small>
            <textarea id="correction-${item.id}" rows="3" placeholder="Verbeterd antwoord of feit"></textarea>
            <div class="history-actions">
                <button data-rate="good" data-id="${item.id}">Goed antwoord</button>
                <button data-rate="bad" data-id="${item.id}">Slecht antwoord</button>
                <button data-rate="corrected" data-id="${item.id}">Correctie opslaan</button>
            </div>
        </article>
    `).join("");

    document.querySelectorAll("[data-rate]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const form = new FormData();
            form.append("interaction_id", btn.dataset.id);
            form.append("rating", btn.dataset.rate);
            form.append("correction", $("correction-" + btn.dataset.id).value);
            await fetch("/api/feedback", {method: "POST", body: form});
            btn.textContent = "Opgeslagen";
            refreshStatus();
        });
    });
}

$("saveConnections").addEventListener("click", async () => {
    const payload = {
        ollama_model: $("ollamaModel").value,
        streamerbot_ws: $("streamerbotWs").value,
        streamerbot_action: $("streamerbotAction").value,
        bot_username: $("botUsername").value
    };
    await fetch("/api/settings", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
    alert("Verbindingen opgeslagen.");
    refreshStatus();
});

$("reconnectStreamerbot").addEventListener("click", async () => {
    await fetch("/api/streamerbot/reconnect", {method: "POST"});
    setTimeout(refreshStatus, 1200);
});

function applyConfig() {
    $("responseStyle").value = config.response_style || "auto";
    $("replyMode").value = config.reply_mode || "smart";
    $("humor").value = config.personality?.humor ?? 70;
    $("sarcasm").value = config.personality?.sarcasm ?? 35;
    $("energy").value = config.personality?.energy ?? 65;
    $("friendly").value = config.personality?.friendly ?? 85;
    $("ollamaModel").value = config.ollama_model || "qwen3:4b";
    $("streamerbotWs").value = config.streamerbot_ws || "ws://127.0.0.1:8080/";
    $("streamerbotAction").value = config.streamerbot_action || "ICE - Send Chat";
    $("botUsername").value = config.bot_username || "";
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

applyConfig();
refreshStatus();
setInterval(refreshStatus, 5000);

if ($("testAvatar")) {
    $("testAvatar").addEventListener("click", async () => {
        const form = new FormData();
        form.append("text", $("avatarTestText").value);
        form.append("emotion", $("avatarEmotion").value);
        await fetch("/api/avatar/test", {method: "POST", body: form});
        $("testAvatar").textContent = "Test verzonden";
        setTimeout(() => $("testAvatar").textContent = "Test avatar en stem", 1200);
    });
}

if ($("saveAvatarSettings")) {
    $("saveAvatarSettings").addEventListener("click", async () => {
        const payload = {
            voice_enabled: $("voiceEnabled").checked,
            voice_name: $("voiceName").value,
            voice_rate: Number($("voiceRate").value),
            voice_volume: Number($("voiceVolume").value),
            avatar_outfit: $("avatarOutfit").value,
            avatar_visible: true
        };
        await fetch("/api/settings", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });
        const outfitForm = new FormData();
        outfitForm.append("outfit", $("avatarOutfit").value);
        await fetch("/api/avatar/outfit", {method: "POST", body: outfitForm});
        alert("Avatar- en steminstellingen opgeslagen.");
        refreshStatus();
    });
}

if ($("voiceEnabled")) {
    $("voiceEnabled").checked = !!config.voice_enabled;
    $("voiceName").value = config.voice_name || "";
    $("voiceRate").value = config.voice_rate ?? 0;
    $("voiceVolume").value = config.voice_volume ?? 100;
    $("avatarOutfit").value = config.avatar_outfit || "farmer";
}
