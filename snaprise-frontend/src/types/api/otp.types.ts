export interface SendOtpRequest {
  email: string;
  purpose: string;
  tenant_id?: string;
}

export interface SendOtpResponse {
  request_id: string;
  status: string;
  provider_id: string | null;
}

export interface VerifyOtpRequest {
  email: string;
  purpose: string;
  code: string;
  tenant_id?: string;
}

export interface VerifyOtpResponse {
  proof_token: string;
}
