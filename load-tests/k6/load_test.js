import http from 'k6/http';
import { check, sleep } from 'k6';

// Base API configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TEST_USER = 'k6_perf_user@example.com';
const TEST_PASS = 'Password123!';

export const options = {
    scenarios: {
        api_journey: {
            executor: 'constant-vus',
            vus: __ENV.VUS ? parseInt(__ENV.VUS) : 5,
            duration: '20s',
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<200', 'p(99)<500'], // Latency SLAs: P95 < 200ms, P99 < 500ms
        http_req_failed: ['rate<0.01'],               // SLA: Error rate < 1%
    },
};

// Setup: Register (if needed) and login once to obtain access token
export function setup() {
    // Attempt registration (errors ignored if user exists)
    http.post(`${BASE_URL}/api/v1/auth/register`, JSON.stringify({
        email: TEST_USER,
        password: TEST_PASS,
        full_name: "K6 Performance User"
    }), {
        headers: { 'Content-Type': 'application/json' }
    });

    // Login to get token
    const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, {
        username: TEST_USER,
        password: TEST_PASS
    });

    let token = '';
    if (loginRes.status === 200) {
        token = loginRes.json('access_token');
    }
    
    return { token };
}

export default function (data) {
    const token = data.token;
    if (!token) {
        console.log('Skipping requests: No auth token');
        return;
    }

    const headers = {
        'Authorization': `Bearer ${token}`
    };

    // 1. Get cached endpoints
    const cacheRes = http.get(`${BASE_URL}/api/v1/cache/stats`, { headers });
    check(cacheRes, {
        'Cache stats returned 200': (r) => r.status === 200,
    });
    sleep(1);

    // 2. Fetch datasets list
    const listRes = http.get(`${BASE_URL}/api/v1/datasets/`, { headers });
    check(listRes, {
        'Datasets list returned 200': (r) => r.status === 200,
    });
    sleep(1);

    // 3. System health telemetry
    const healthRes = http.get(`${BASE_URL}/health/ready`);
    check(healthRes, {
        'Health ready returned 200': (r) => r.status === 200,
    });
    sleep(1);
}
