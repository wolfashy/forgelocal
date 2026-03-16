function getScoreColor(score) {
  if (score >= 85) return "linear-gradient(135deg, #17a46b, #0d8a58)";
  if (score >= 70) return "linear-gradient(135deg, #ff9a1f, #ff7a00)";
  return "linear-gradient(135deg, #e35d5d, #c73d3d)";
}

async function runScan(event) {
  event.preventDefault();

  const urlInput = document.getElementById("urlInput");
  const scanBtn = document.getElementById("scanBtn");
  const btnText = document.getElementById("btnText");
  const loading = document.getElementById("loading");
  const results = document.getElementById("results");

  const url = urlInput.value.trim();

  scanBtn.disabled = true;
  btnText.textContent = "Scanning...";
  loading.style.display = "flex";
  results.style.display = "none";

  try {
    const response = await fetch("/scan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Scan failed");
    }

    const scoreCircle = document.getElementById("scoreCircle");
    scoreCircle.textContent = data.score;
    scoreCircle.style.background = getScoreColor(data.score);

    document.getElementById("scoreLabel").textContent = data.label;
    document.getElementById("scoreDescription").textContent = data.description;

    document.getElementById("metricMobile").textContent =
      data.metrics?.mobileScore ? `${data.metrics.mobileScore}/100` : "N/A";
    document.getElementById("metricSpeed").textContent =
      data.metrics?.desktopScore ? `${data.metrics.desktopScore}/100` : "N/A";
    document.getElementById("metricCta").textContent =
      data.metrics?.seo ? `${data.metrics.seo}/100 SEO` : "Review";

    const issuesContainer = document.getElementById("issuesContainer");
    issuesContainer.innerHTML = "";

    (data.issues || []).forEach(issue => {
      const issueElement = document.createElement("div");
      issueElement.className = "issue-item";
      issueElement.innerHTML = `
        <h5>${issue.title}</h5>
        <p>${issue.detail}</p>
      `;
      issuesContainer.appendChild(issueElement);
    });

    results.style.display = "block";
  } catch (error) {
    console.error(error);
    alert(error.message || "Error scanning website.");
  } finally {
    loading.style.display = "none";
    scanBtn.disabled = false;
    btnText.textContent = "Scan My Website";
  }
}

async function runPsi(url, strategy) {
    const endpoint =
        `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${encodeURIComponent(url)}&strategy=${strategy}&category=performance&category=accessibility&category=best-practices&category=seo`;

    const response = await fetch(endpoint, {
        method: "GET",
        headers: {
            "Accept": "application/json",
        },
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`PageSpeed API error (${strategy}): ${text}`);
    }

    return response.json();
}

function getCategoryScore(data, category) {
    const value = data?.lighthouseResult?.categories?.[category]?.score;
    if (typeof value !== "number") return 0;
    return Math.round(value * 100);
}

function buildIssues(mobileData, desktopData) {
    const issues = [];

    const mobileAudits = mobileData?.lighthouseResult?.audits || {};
    const desktopAudits = desktopData?.lighthouseResult?.audits || {};

    pushIfAuditPoor(
        issues,
        mobileAudits["largest-contentful-paint"],
        "Slow main load speed",
        "Your biggest visible content takes too long to load, which hurts first impressions and causes drop-off."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["interactive"],
        "Slow to become usable",
        "Visitors may see the page before it is properly usable, which makes the site feel laggy."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["cumulative-layout-shift"],
        "Layout jumps on mobile",
        "Content shifts while loading, which makes the page feel unstable and frustrating."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["uses-responsive-images"],
        "Images are not optimized for phones",
        "Large or badly sized images can slow mobile performance and waste data."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["tap-targets"],
        "Buttons may be hard to tap",
        "Small touch targets make the site harder to use on phones."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["color-contrast"],
        "Text may be hard to read",
        "Low contrast text can reduce trust and make key content harder to scan."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["document-title"],
        "Weak page title setup",
        "Your page title may not clearly explain what the business offers."
    );

    pushIfAuditPoor(
        issues,
        mobileAudits["meta-description"],
        "Missing or weak meta description",
        "Your search listing may be less persuasive, which can hurt clicks."
    );

    if (issues.length < 3) {
        const mobileScore = getCategoryScore(mobileData, "performance");
        const desktopScore = getCategoryScore(desktopData, "performance");

        if (mobileScore < 80) {
            issues.push({
                title: "Mobile performance needs work",
                detail: "Your mobile experience likely feels slower or heavier than it should for local customers browsing on phones.",
            });
        }

        if (desktopScore < 80) {
            issues.push({
                title: "Desktop speed can improve",
                detail: "Your desktop page has room for improvement in speed and polish.",
            });
        }

        issues.push({
            title: "Call-to-action flow should be reviewed",
            detail: "Even if the technical score is decent, a clearer call, quote, or booking path can improve conversions.",
        });
    }

    return issues.slice(0, 6);
}

function pushIfAuditPoor(issues, audit, title, detail) {
    if (!audit) return;

    const score = typeof audit.score === "number" ? audit.score : 1;
    if (score >= 0.9) return;

    issues.push({
        title,
        detail,
    });
}

function json(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
    });
}