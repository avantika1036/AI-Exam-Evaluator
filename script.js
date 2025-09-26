// --- SIMULATED DATA (Replace with actual AJAX/Fetch calls in production) ---
const classData = [
    { student: "Alice Johnson", total_score: 45, max_total: 50, percentage: 90.0, rank: 1, Q1: 4.5, Q2: 5.0, Q3: 4.0 },
    { student: "Bob Smith", total_score: 38, max_total: 50, percentage: 76.0, rank: 3, Q1: 3.0, Q2: 4.0, Q3: 4.0 },
    { student: "Charlie Brown", total_score: 48, max_total: 50, percentage: 96.0, rank: 2, Q1: 5.0, Q2: 5.0, Q3: 5.0 },
    { student: "Diana Prince", total_score: 25, max_total: 50, percentage: 50.0, rank: 4, Q1: 2.0, Q2: 1.0, Q3: 3.0 },
    // ... more students ...
];

const rawInsights = [
    { question: "Q4: Explain quantum entanglement.", avg_score: 1.2, max_score: 5 },
    { question: "Q1: Define classical mechanics.", avg_score: 4.5, max_score: 5 },
];

const conceptCounts = [
    { concept: "Thermodynamics", count: 15 },
    { concept: "Kinematics", count: 12 },
    { concept: "Entanglement", count: 5 },
    // ...
];

// --- Global State ---
let currentTab = 'leaderboard';

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupNavigation();
});

function loadData() {
    // In production, this would be: fetch('/api/class_summary').then(res => res.json()).then(data => { ... })
    
    // Sort data for ranking
    const summaryData = classData.sort((a, b) => b.percentage - a.percentage).map((s, i) => ({...s, rank: i + 1}));

    renderMetrics(summaryData);
    renderLeaderboard(summaryData);
    renderAnalytics(summaryData);
    // Setup student profile dropdown
    const selector = document.getElementById('student-selector');
    summaryData.forEach(student => {
        const option = document.createElement('option');
        option.value = student.student;
        option.textContent = student.student;
        selector.appendChild(option);
    });
}

// --- RENDER FUNCTIONS ---

function renderMetrics(data) {
    if (data.length === 0) return;
    const avgScore = (data.reduce((sum, s) => sum + s.percentage, 0) / data.length).toFixed(1);
    const maxScore = data[0].total_score;
    const maxPossible = data[0].max_total;
    const passRate = (data.filter(s => s.percentage >= 60).length / data.length * 100).toFixed(1);

    document.getElementById('avg-score').textContent = `${avgScore}%`;
    document.getElementById('max-score').textContent = `${maxScore}/${maxPossible}`;
    document.getElementById('pass-rate').textContent = `${passRate}%`;
    document.getElementById('total-students').textContent = data.length;
}

function renderLeaderboard(data) {
    const podiumContainer = document.getElementById('podium-container');
    podiumContainer.innerHTML = '';
    
    // Ranks 2, 1, 3
    const topStudents = [data[1], data[0], data[2]].filter(s => s); 
    const rankClasses = ['rank-2', 'rank-1', 'rank-3'];
    
    topStudents.forEach((student, index) => {
        const rank = index === 0 ? 2 : (index === 1 ? 1 : 3);
        const card = document.createElement('div');
        card.className = `podium-card ${rankClasses[index]}`;
        card.innerHTML = `
            <div class="podium-rank">#${rank}</div>
            <div class="podium-name">${student.student}</div>
            <div class="podium-score">${student.percentage.toFixed(1)}%</div>
        `;
        podiumContainer.appendChild(card);
    });

    // Full Ranking Table
    const tableBody = document.getElementById('full-ranking-table');
    tableBody.innerHTML = `
        <thead>
            <tr><th>Rank</th><th>Student</th><th>Score</th><th>Percentage</th></tr>
        </thead>
        <tbody>
            ${data.map(s => `
                <tr>
                    <td>#${s.rank}</td>
                    <td>${s.student}</td>
                    <td>${s.total_score}/${s.max_total}</td>
                    <td>${s.percentage.toFixed(1)}%</td>
                </tr>
            `).join('')}
        </tbody>
    `;
}

function renderAnalytics(data) {
    // 1. Question Average Chart (Simulated for Q1, Q2, Q3)
    const qLabels = ['Q1', 'Q2', 'Q3'];
    const qAverages = [
        data.reduce((sum, s) => sum + s.Q1, 0) / data.length,
        data.reduce((sum, s) => sum + s.Q2, 0) / data.length,
        data.reduce((sum, s) => sum + s.Q3, 0) / data.length,
    ];
    
    new Chart(document.getElementById('question-avg-chart'), {
        type: 'bar',
        data: {
            labels: qLabels,
            datasets: [{
                label: 'Avg Score (Simulated)',
                data: qAverages,
                backgroundColor: 'rgba(0, 224, 255, 0.7)',
                borderColor: 'var(--accent)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: { title: { display: true, text: 'Average Score Per Question' } },
            scales: { y: { beginAtZero: true, max: 5 } }
        }
    });

    // 2. Score Distribution Chart (Histogram Simulation)
    const percentages = data.map(s => s.percentage);
    const bins = [0, 50, 60, 70, 80, 90, 100];
    const distribution = new Array(bins.length - 1).fill(0);
    percentages.forEach(p => {
        if (p < 50) distribution[0]++;
        else if (p < 60) distribution[1]++;
        else if (p < 70) distribution[2]++;
        else if (p < 80) distribution[3]++;
        else if (p < 90) distribution[4]++;
        else distribution[5]++;
    });

    new Chart(document.getElementById('score-distribution-chart'), {
        type: 'line',
        data: {
            labels: ['0-50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%'],
            datasets: [{
                label: 'Student Count',
                data: distribution,
                fill: true,
                backgroundColor: 'rgba(0, 224, 255, 0.2)',
                borderColor: 'var(--accent)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: { title: { display: true, text: 'Student Score Distribution' } }
        }
    });
}

function renderInsights() {
    // Hardest Questions
    const hardList = document.getElementById('hard-questions');
    hardList.innerHTML = rawInsights.filter(r => r.avg_score < 3).map(r => `
        <div class="insight-item">
            <strong>${r.question}</strong>: Avg. Score ${r.avg_score}/${r.max_score}
        </div>
    `).join('');

    // Concept Frequency Chart
    new Chart(document.getElementById('concept-chart'), {
        type: 'doughnut',
        data: {
            labels: conceptCounts.map(c => c.concept),
            datasets: [{
                data: conceptCounts.map(c => c.count),
                backgroundColor: ['#00e0ff', '#DAA520', '#C0C0C0', '#CD7F32'],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { title: { display: true, text: 'Top Concept Frequencies' } }
        }
    });
}

// --- INTERACTION HANDLERS ---

function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const newTab = e.target.getAttribute('data-tab');
            if (newTab === currentTab) return;

            // Hide all tabs
            document.querySelectorAll('.dashboard-tab').forEach(tab => {
                tab.classList.add('hidden');
            });

            // Deactivate all buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            // Show new tab and activate button
            document.getElementById(newTab).classList.remove('hidden');
            e.target.classList.add('active');
            currentTab = newTab;
            
            // Render content specific to the tab (e.g., charts for insights)
            if (newTab === 'insights') renderInsights();
        });
    });

    document.getElementById('student-selector').addEventListener('change', (e) => {
        // In a real app, fetch the student's detailed Q/A data
        const selectedName = e.target.value;
        const student = classData.find(s => s.student === selectedName);
        if (student) {
            // Placeholder rendering for the profile section
            document.getElementById('student-details').innerHTML = `
                <div class="profile-stat">Rank: <strong>#${student.rank}</strong></div>
                <div class="profile-stat">Score: <strong>${student.total_score}/${student.max_total}</strong></div>
                <div class="profile-stat">Percentage: <strong>${student.percentage.toFixed(1)}%</strong></div>
                <div style="grid-column: 1 / 4; margin-top: 20px;">
                    <h3>Detailed Q/A Breakdown (Simulated)</h3>
                    <div class="insight-item">Q1: ${student.Q1}/5.0. Feedback: Great start!</div>
                    <div class="insight-item">Q2: ${student.Q2}/5.0. Feedback: Excellent clarity.</div>
                </div>
            `;
        } else {
            document.getElementById('student-details').innerHTML = '';
        }
    });
}