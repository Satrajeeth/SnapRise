export interface UserCreate {
  email: string;
  password?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  is_verified?: boolean;
}

export interface RegisterRequest {
  user_create: UserCreate;
  proof_token: string;
}

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface ForgotPasswordRequest {
  email: string;
  proof_token: string;
}

export interface ForgotPasswordResponse {
  token: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}
