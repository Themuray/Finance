// ===== Internationalization (i18n) =====
let currentLang = localStorage.getItem('pf-lang') || 'de';

function setLanguage(lang) {
    currentLang = lang;
    document.documentElement.lang = lang;
    localStorage.setItem('pf-lang', lang);

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.textContent = TRANSLATIONS[lang][key];
        }
    });

    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.getAttribute('data-i18n-html');
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.innerHTML = TRANSLATIONS[lang][key];
        }
    });

    // Update page title
    const titleKey = 'page.title';
    if (TRANSLATIONS[lang] && TRANSLATIONS[lang][titleKey]) {
        document.title = TRANSLATIONS[lang][titleKey];
    }

    // Update toggle button
    document.querySelectorAll('.lang-option').forEach(opt => {
        opt.classList.toggle('active', opt.dataset.lang === lang);
    });

    // Update checklist progress text
    updateChecklistProgress();
}

// Language toggle
const langToggle = document.getElementById('lang-toggle');
if (langToggle) {
    langToggle.addEventListener('click', () => {
        setLanguage(currentLang === 'de' ? 'en' : 'de');
    });
}

// ===== Mobile Nav Toggle =====
const navToggle = document.getElementById('nav-toggle');
const navLinks = document.getElementById('nav-links');

navToggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    navToggle.classList.toggle('active');
});

// Close mobile nav when a link is clicked
navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        navToggle.classList.remove('active');
    });
});

// ===== Active Nav Link on Scroll =====
const sections = document.querySelectorAll('.topic-section');
const navAnchors = document.querySelectorAll('.nav-links a');

function updateActiveNav() {
    const scrollY = window.scrollY + 120;

    sections.forEach(section => {
        const top = section.offsetTop;
        const height = section.offsetHeight;
        const id = section.getAttribute('id');

        if (scrollY >= top && scrollY < top + height) {
            navAnchors.forEach(a => {
                a.classList.remove('active');
                if (a.getAttribute('href') === '#' + id) {
                    a.classList.add('active');
                }
            });
        }
    });
}

window.addEventListener('scroll', updateActiveNav, { passive: true });

// ===== Section Reveal on Scroll =====
const revealCards = document.querySelectorAll('.topic-card.reveal');

const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            revealObserver.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
});

revealCards.forEach(card => revealObserver.observe(card));

// ===== Navbar Background on Scroll =====
const navbar = document.getElementById('navbar');

function updateNavbar() {
    if (window.scrollY > 50) {
        navbar.style.background = 'rgba(10, 10, 15, 0.95)';
    } else {
        navbar.style.background = 'rgba(10, 10, 15, 0.85)';
    }
}

window.addEventListener('scroll', updateNavbar, { passive: true });

// ===== Utility: Format CHF =====
function formatCHF(amount) {
    const rounded = Math.round(amount);
    return 'CHF ' + rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'");
}

// ===== Calculator: Pillar 3a Tax Savings =====
function initCalc3a() {
    const cantonSelect = document.getElementById('calc-canton');
    if (!cantonSelect || typeof CANTON_TAX_RATES === 'undefined') return;

    // Populate canton dropdown
    Object.keys(CANTON_TAX_RATES).forEach(code => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = CANTON_TAX_RATES[code].name;
        cantonSelect.appendChild(opt);
    });
    cantonSelect.value = 'ZH';

    function calcTax(rates, income) {
        let tax = 0;
        for (const bracket of rates) {
            if (income <= bracket.min) break;
            const taxableInBracket = Math.min(income, bracket.max) - bracket.min;
            tax += taxableInBracket * bracket.rate;
        }
        return tax;
    }

    function update3a() {
        const canton = cantonSelect.value;
        const income = parseFloat(document.getElementById('calc-income').value) || 0;
        const contribution = parseFloat(document.getElementById('calc-contribution').value) || 0;

        if (!CANTON_TAX_RATES[canton]) return;

        const rates = CANTON_TAX_RATES[canton].rates;
        const taxWithout = calcTax(rates, income);
        const taxWith = calcTax(rates, Math.max(0, income - contribution));
        const savings = taxWithout - taxWith;

        document.getElementById('calc-3a-value').textContent = formatCHF(savings);
    }

    // Sync sliders and inputs
    syncSliderInput('calc-income-slider', 'calc-income', update3a);
    syncSliderInput('calc-contribution-slider', 'calc-contribution', update3a);
    cantonSelect.addEventListener('change', update3a);

    update3a();
}

// ===== Calculator: Emergency Fund =====
function initCalcEmergency() {
    const fields = ['calc-rent', 'calc-insurance', 'calc-food', 'calc-transport', 'calc-other'];

    function updateEmergency() {
        let total = 0;
        fields.forEach(id => {
            total += parseFloat(document.getElementById(id).value) || 0;
        });
        const min = total * 3;
        const max = total * 6;
        document.getElementById('calc-emergency-value').textContent = formatCHF(min) + ' – ' + formatCHF(max);
    }

    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateEmergency);
    });

    updateEmergency();
}

// ===== Calculator: Franchise Optimizer =====
function initCalcFranchise() {
    function updateFranchise() {
        const costs = parseFloat(document.getElementById('calc-healthcare').value) || 0;
        const monthlyDiff = parseFloat(document.getElementById('calc-premium-diff').value) || 0;
        const annualDiff = monthlyDiff * 12;

        // Franchise 300: higher premium (base + diff), lower out-of-pocket
        // Franchise 2500: lower premium (base), higher out-of-pocket
        // We only need the DIFFERENCE, so set base premium to a reference value
        const basePremium = 4800; // CHF 400/month reference for franchise 2500

        // Out-of-pocket = franchise + 10% of (costs - franchise), max 700 Selbstbehalt
        function calcOOP(franchise, actualCosts) {
            if (actualCosts <= 0) return 0;
            const franchiseUsed = Math.min(actualCosts, franchise);
            const aboveFranchise = Math.max(0, actualCosts - franchise);
            const selbstbehalt = Math.min(aboveFranchise * 0.10, 700);
            return franchiseUsed + selbstbehalt;
        }

        const premium300 = basePremium + annualDiff;
        const premium2500 = basePremium;
        const oop300 = calcOOP(300, costs);
        const oop2500 = calcOOP(2500, costs);
        const total300 = premium300 + oop300;
        const total2500 = premium2500 + oop2500;

        document.getElementById('franchise-premium-300').textContent = formatCHF(premium300);
        document.getElementById('franchise-premium-2500').textContent = formatCHF(premium2500);
        document.getElementById('franchise-oop-300').textContent = formatCHF(oop300);
        document.getElementById('franchise-oop-2500').textContent = formatCHF(oop2500);
        document.getElementById('franchise-total-300').textContent = formatCHF(total300);
        document.getElementById('franchise-total-2500').textContent = formatCHF(total2500);

        const diff = Math.abs(total300 - total2500);
        const verdictEl = document.getElementById('franchise-verdict-text');
        if (total300 < total2500) {
            verdictEl.textContent = (currentLang === 'de' ? 'Franchise 300 spart ' : 'Franchise 300 saves ') + formatCHF(diff) + (currentLang === 'de' ? '/Jahr' : '/year');
            verdictEl.style.color = 'var(--accent-green)';
        } else if (total2500 < total300) {
            verdictEl.textContent = (currentLang === 'de' ? 'Franchise 2\'500 spart ' : 'Franchise 2\'500 saves ') + formatCHF(diff) + (currentLang === 'de' ? '/Jahr' : '/year');
            verdictEl.style.color = 'var(--accent-green)';
        } else {
            verdictEl.textContent = currentLang === 'de' ? 'Beide gleich' : 'Both equal';
            verdictEl.style.color = 'var(--accent-blue)';
        }
    }

    syncSliderInput('calc-healthcare-slider', 'calc-healthcare', updateFranchise);
    syncSliderInput('calc-premium-diff-slider', 'calc-premium-diff', updateFranchise);

    updateFranchise();
}

// ===== Calculator: Compound Growth =====
function initCalcCompound() {
    function updateCompound() {
        const monthly = parseFloat(document.getElementById('calc-monthly').value) || 0;
        const annualReturn = parseFloat(document.getElementById('calc-return').value) || 0;
        const years = parseInt(document.getElementById('calc-years').value) || 0;

        const monthlyRate = annualReturn / 100 / 12;
        const totalMonths = years * 12;
        const totalInvested = monthly * totalMonths;

        let value = 0;
        if (monthlyRate > 0) {
            value = monthly * ((Math.pow(1 + monthlyRate, totalMonths) - 1) / monthlyRate);
        } else {
            value = totalInvested;
        }

        const growth = value - totalInvested;

        document.getElementById('compound-invested').textContent = formatCHF(totalInvested);
        document.getElementById('compound-growth').textContent = formatCHF(growth);
        document.getElementById('compound-total').textContent = formatCHF(value);

        drawCompoundChart(monthly, annualReturn, years);
    }

    syncSliderInput('calc-monthly-slider', 'calc-monthly', updateCompound);
    syncSliderInput('calc-return-slider', 'calc-return', updateCompound);
    syncSliderInput('calc-years-slider', 'calc-years', updateCompound);

    updateCompound();
}

function drawCompoundChart(monthly, annualReturn, years) {
    const canvas = document.getElementById('compound-chart');
    if (!canvas) return;

    const container = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth - 32;
    const h = Math.min(300, w * 0.5);

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const pad = { top: 20, right: 20, bottom: 30, left: 70 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const monthlyRate = annualReturn / 100 / 12;

    // Calculate data points per year
    const dataInvested = [];
    const dataTotal = [];
    for (let y = 0; y <= years; y++) {
        const months = y * 12;
        const invested = monthly * months;
        let total;
        if (monthlyRate > 0) {
            total = monthly * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate);
        } else {
            total = invested;
        }
        dataInvested.push(invested);
        dataTotal.push(total);
    }

    const maxVal = Math.max(...dataTotal, 1);

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#222233';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const y = pad.top + (plotH / gridLines) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();

        // Y-axis labels
        const val = maxVal - (maxVal / gridLines) * i;
        ctx.fillStyle = '#66667a';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(formatCHF(val), pad.left - 8, y + 4);
    }

    // X-axis labels
    ctx.fillStyle = '#66667a';
    ctx.textAlign = 'center';
    const labelStep = years <= 10 ? 1 : years <= 30 ? 5 : 10;
    for (let y = 0; y <= years; y += labelStep) {
        const x = pad.left + (y / years) * plotW;
        ctx.fillText(y + (currentLang === 'de' ? 'J' : 'y'), x, h - 8);
    }

    function toX(i) { return pad.left + (i / years) * plotW; }
    function toY(v) { return pad.top + plotH - (v / maxVal) * plotH; }

    // Fill area: total (growth portion)
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(0));
    for (let i = 0; i <= years; i++) ctx.lineTo(toX(i), toY(dataTotal[i]));
    ctx.lineTo(toX(years), toY(0));
    ctx.closePath();
    ctx.fillStyle = 'rgba(34, 197, 94, 0.15)';
    ctx.fill();

    // Fill area: invested
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(0));
    for (let i = 0; i <= years; i++) ctx.lineTo(toX(i), toY(dataInvested[i]));
    ctx.lineTo(toX(years), toY(0));
    ctx.closePath();
    ctx.fillStyle = 'rgba(79, 140, 255, 0.2)';
    ctx.fill();

    // Line: total
    ctx.beginPath();
    for (let i = 0; i <= years; i++) {
        if (i === 0) ctx.moveTo(toX(i), toY(dataTotal[i]));
        else ctx.lineTo(toX(i), toY(dataTotal[i]));
    }
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Line: invested
    ctx.beginPath();
    for (let i = 0; i <= years; i++) {
        if (i === 0) ctx.moveTo(toX(i), toY(dataInvested[i]));
        else ctx.lineTo(toX(i), toY(dataInvested[i]));
    }
    ctx.strokeStyle = '#4f8cff';
    ctx.lineWidth = 2;
    ctx.stroke();
}

// ===== Sync slider <-> input =====
function syncSliderInput(sliderId, inputId, callback) {
    const slider = document.getElementById(sliderId);
    const input = document.getElementById(inputId);
    if (!slider || !input) return;

    slider.addEventListener('input', () => {
        input.value = slider.value;
        callback();
    });

    input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        if (!isNaN(val)) {
            slider.value = Math.max(slider.min, Math.min(slider.max, val));
        }
        callback();
    });
}

// ===== Canton Tax Comparison Table =====
function initCantonTable() {
    const tbody = document.getElementById('canton-table-body');
    if (!tbody || typeof CANTON_COMPARISON === 'undefined') return;

    const incomes = [80000, 120000, 200000];

    // Find min/max per income level
    const mins = {};
    const maxs = {};
    incomes.forEach(inc => {
        const vals = CANTON_COMPARISON.map(c => c.rates[inc]);
        mins[inc] = Math.min(...vals);
        maxs[inc] = Math.max(...vals);
    });

    CANTON_COMPARISON.forEach(canton => {
        const tr = document.createElement('tr');
        const tdName = document.createElement('td');
        tdName.className = 'canton-name';
        tdName.textContent = canton.name + ' (' + canton.code + ')';
        tr.appendChild(tdName);

        incomes.forEach(inc => {
            const td = document.createElement('td');
            const rate = canton.rates[inc];
            td.textContent = rate.toFixed(1) + '%';
            if (rate === mins[inc]) td.className = 'tax-low';
            else if (rate === maxs[inc]) td.className = 'tax-high';
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

// ===== Market History Chart =====
let marketNormalized = true;
const marketSeriesVisible = { SMI: true, SPX: true, UKX: true, SX5E: true };
const seriesColors = {
    SMI: '#4f8cff',
    SPX: '#22c55e',
    UKX: '#ff1f3d',
    SX5E: '#c084fc'
};

function initMarketChart() {
    if (typeof PRICE_DATA === 'undefined') return;

    // Normalize button
    const btnNorm = document.getElementById('btn-normalized');
    const btnAbs = document.getElementById('btn-absolute');
    if (btnNorm) {
        btnNorm.addEventListener('click', () => {
            marketNormalized = true;
            btnNorm.classList.add('active');
            btnAbs.classList.remove('active');
            drawMarketChart();
        });
    }
    if (btnAbs) {
        btnAbs.addEventListener('click', () => {
            marketNormalized = false;
            btnAbs.classList.add('active');
            btnNorm.classList.remove('active');
            drawMarketChart();
        });
    }

    // Legend toggles
    document.querySelectorAll('#market-legend .legend-item').forEach(item => {
        item.addEventListener('click', () => {
            const series = item.dataset.series;
            marketSeriesVisible[series] = !marketSeriesVisible[series];
            item.classList.toggle('active', marketSeriesVisible[series]);
            drawMarketChart();
        });
    });

    drawMarketChart();
}

function drawMarketChart() {
    const canvas = document.getElementById('market-chart');
    if (!canvas || typeof PRICE_DATA === 'undefined') return;

    const container = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = container.clientWidth - 40;
    const h = Math.min(400, w * 0.55);

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const pad = { top: 20, right: 20, bottom: 30, left: 70 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const dates = PRICE_DATA.dates;
    const numPoints = dates.length;

    // Find common start index for normalization (first index where all visible series have data)
    let normStartIdx = 0;
    if (marketNormalized) {
        for (let i = 0; i < numPoints; i++) {
            let allHaveData = true;
            for (const key of Object.keys(marketSeriesVisible)) {
                if (marketSeriesVisible[key] && PRICE_DATA.series[key][i] === null) {
                    allHaveData = false;
                    break;
                }
            }
            if (allHaveData) { normStartIdx = i; break; }
        }
    }

    // Build display data
    const displayData = {};
    let globalMax = -Infinity;
    let globalMin = Infinity;

    for (const key of Object.keys(marketSeriesVisible)) {
        if (!marketSeriesVisible[key]) continue;
        const raw = PRICE_DATA.series[key];
        const baseVal = raw[normStartIdx];
        const data = [];

        for (let i = normStartIdx; i < numPoints; i++) {
            if (raw[i] !== null) {
                const val = marketNormalized ? (raw[i] / baseVal) * 100 : raw[i];
                data.push({ idx: i - normStartIdx, val: val });
                if (val > globalMax) globalMax = val;
                if (val < globalMin) globalMin = val;
            }
        }
        displayData[key] = data;
    }

    if (globalMax === -Infinity) return;

    const totalPoints = numPoints - normStartIdx;
    const yRange = globalMax - globalMin;
    const yMin = Math.max(0, globalMin - yRange * 0.05);
    const yMax = globalMax + yRange * 0.05;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#222233';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const y = pad.top + (plotH / gridLines) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();

        const val = yMax - ((yMax - yMin) / gridLines) * i;
        ctx.fillStyle = '#66667a';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'right';
        if (marketNormalized) {
            ctx.fillText(Math.round(val), pad.left - 8, y + 4);
        } else {
            ctx.fillText(formatCHF(val), pad.left - 8, y + 4);
        }
    }

    // X-axis year labels
    ctx.fillStyle = '#66667a';
    ctx.textAlign = 'center';
    const startYear = parseInt(dates[normStartIdx].substring(0, 4));
    const endYear = parseInt(dates[numPoints - 1].substring(0, 4));
    const yearSpan = endYear - startYear;
    const yearStep = yearSpan <= 10 ? 1 : yearSpan <= 20 ? 2 : 5;

    for (let yr = Math.ceil(startYear / yearStep) * yearStep; yr <= endYear; yr += yearStep) {
        const dateStr = yr + '-01';
        const idx = dates.indexOf(dateStr);
        if (idx >= normStartIdx) {
            const x = pad.left + ((idx - normStartIdx) / totalPoints) * plotW;
            ctx.fillText(yr.toString(), x, h - 8);
        }
    }

    function toX(i) { return pad.left + (i / totalPoints) * plotW; }
    function toY(v) { return pad.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH; }

    // Draw lines
    for (const key of Object.keys(displayData)) {
        const data = displayData[key];
        if (data.length < 2) continue;

        ctx.beginPath();
        ctx.moveTo(toX(data[0].idx), toY(data[0].val));
        for (let i = 1; i < data.length; i++) {
            ctx.lineTo(toX(data[i].idx), toY(data[i].val));
        }
        ctx.strokeStyle = seriesColors[key];
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

// ===== Financial Health Checklist =====
function initChecklist() {
    const checkboxes = document.querySelectorAll('[data-check]');
    if (!checkboxes.length) return;

    const saved = JSON.parse(localStorage.getItem('pf-checklist') || '{}');

    checkboxes.forEach(cb => {
        const key = cb.dataset.check;
        if (saved[key]) cb.checked = true;

        cb.addEventListener('change', () => {
            const state = JSON.parse(localStorage.getItem('pf-checklist') || '{}');
            state[key] = cb.checked;
            localStorage.setItem('pf-checklist', JSON.stringify(state));
            updateChecklistProgress();
        });
    });

    updateChecklistProgress();
}

function updateChecklistProgress() {
    const checkboxes = document.querySelectorAll('[data-check]');
    if (!checkboxes.length) return;

    const total = checkboxes.length;
    let checked = 0;
    checkboxes.forEach(cb => { if (cb.checked) checked++; });

    const pct = (checked / total) * 100;
    const bar = document.getElementById('checklist-bar');
    if (bar) bar.style.width = pct + '%';

    const textEl = document.getElementById('checklist-text');
    if (textEl) {
        if (currentLang === 'de') {
            textEl.textContent = checked + ' von ' + total + ' erledigt';
        } else {
            textEl.textContent = checked + ' / ' + total + ' completed';
        }
    }
}

// ===== Resize Handler =====
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        // Redraw charts on resize
        const monthly = parseFloat(document.getElementById('calc-monthly')?.value) || 500;
        const annualReturn = parseFloat(document.getElementById('calc-return')?.value) || 7;
        const years = parseInt(document.getElementById('calc-years')?.value) || 30;
        drawCompoundChart(monthly, annualReturn, years);
        drawMarketChart();
    }, 200);
}, { passive: true });

// ===== Initialize Everything =====
document.addEventListener('DOMContentLoaded', () => {
    setLanguage(currentLang);
    initCalc3a();
    initCalcEmergency();
    initCalcFranchise();
    initCalcCompound();
    initCantonTable();
    initMarketChart();
    initChecklist();
});
