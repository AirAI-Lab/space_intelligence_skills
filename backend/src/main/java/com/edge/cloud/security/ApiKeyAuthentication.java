package com.edge.cloud.security;

import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.authority.AuthorityUtils;

public class ApiKeyAuthentication extends AbstractAuthenticationToken {

    private final String apiKey;

    public ApiKeyAuthentication(String apiKey) {
        super(AuthorityUtils.createAuthorityList("ROLE_API"));
        this.apiKey = apiKey;
        setAuthenticated(true);
    }

    @Override
    public Object getCredentials() {
        return apiKey;
    }

    @Override
    public Object getPrincipal() {
        return "api-client";
    }
}
