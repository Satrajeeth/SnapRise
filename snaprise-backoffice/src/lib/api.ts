const AUTH_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;

// Shared fetch wrapper. Throws an Error whose .message is the API's error detail
// (string, validation array, or object) so callers can branch on it. Mirrors
// snaprise-frontend's apiRequest so the two apps behave identically.
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
    const errorMessage =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
        ? data.detail[0]?.msg
        : data.detail?.reason || data.message || "Something went wrong";

    throw new Error(errorMessage);
  }

  return data;
}

export const authApi = {
  // OAuth2 password flow — form-encoded, same as snaprise-frontend.
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
  refresh: (refreshToken: string) =>
    apiRequest(AUTH_BASE_URL, "/auth/jwt/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
  // Returns the authenticated user incl. is_superuser — the bit the backoffice
  // gates on. (The is_superuser JWT claim authorizes admin_service; this call is
  // what the *client* uses to decide whether to even show the admin UI.)
  me: (token: string) =>
    apiRequest(AUTH_BASE_URL, "/users/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
};
