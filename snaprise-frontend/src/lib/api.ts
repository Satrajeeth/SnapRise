const OTP_BASE_URL = process.env.NEXT_PUBLIC_OTP_SERVICE_URL;
const AUTH_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;

export async function apiRequest(
  baseUrl: string | undefined,
  endpoint: string,
  options: RequestInit = {}
) {
  if (!baseUrl) {
    throw new Error("API Base URL is not defined");
  }

  const url = `${baseUrl}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // Some APIs return detail as a string, others as an object or array of objects.
    const errorMessage = 
      typeof data.detail === "string" ? data.detail : 
      Array.isArray(data.detail) ? data.detail[0]?.msg : 
      data.detail?.reason || data.message || "Something went wrong";
      
    throw new Error(errorMessage);
  }

  return data;
}

export const otpApi = {
  send: (email: string, purpose: string) =>
    apiRequest(OTP_BASE_URL, "/send", {
      method: "POST",
      body: JSON.stringify({
        email,
        purpose,
        tenant_id: "default",
        locale: "en",
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  verify: (email: string, purpose: string, code: string) =>
    apiRequest(OTP_BASE_URL, "/verify", {
      method: "POST",
      body: JSON.stringify({
        email,
        purpose,
        code,
        tenant_id: "default",
      }),
    }),
};

export const authApi = {
  register: (userCreate: any, proofToken: string) =>
    apiRequest(AUTH_BASE_URL, "/auth/register", {
      method: "POST",
      body: JSON.stringify({
        user_create: userCreate,
        proof_token: proofToken,
      }),
    }),
  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    return apiRequest(AUTH_BASE_URL, "/auth/jwt/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });
  },
  forgotPassword: (email: string, proofToken: string) =>
    apiRequest(AUTH_BASE_URL, "/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({
        email,
        proof_token: proofToken,
      }),
    }),
  resetPassword: (token: string, password: string) =>
    apiRequest(AUTH_BASE_URL, "/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({
        token,
        password,
      }),
    }),
  checkEmail: (email: string) =>
    apiRequest(AUTH_BASE_URL, `/auth/check-email?email=${encodeURIComponent(email)}`, {
      method: "GET",
    }),
  me: (token: string) =>
    apiRequest(AUTH_BASE_URL, "/users/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
};
