# Test script for Vending Hive Accounts Package
Write-Host "Starting Vending Hive Accounts Package Tests..." -ForegroundColor Green

# Function to make HTTP requests
function Invoke-APIRequest {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )
    
    try {
        $params = @{
            Method = $Method
            Uri = $Uri
            Headers = $Headers
            ContentType = "application/json"
        }
        
        if ($Body) {
            $params.Body = $Body
        }
        
        $response = Invoke-RestMethod @params
        return @{
            Success = $true
            Data = $response
            StatusCode = 200
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { 500 }
        return @{
            Success = $false
            Error = $_.Exception.Message
            StatusCode = $statusCode
        }
    }
}

# Base URL for API
$baseUrl = "http://127.0.0.1:8000"

Write-Host "`n1. Testing User Registration..." -ForegroundColor Yellow

$registrationData = @{
    email = "123testuser@example.com"
    username = "123testuser"
    first_name = "Test"
    last_name = "User"
    password = "123testpass123"
    password_confirm = "123testpass123"
    terms_accepted = $true
    marketing_emails = $false
} | ConvertTo-Json

$regResponse = Invoke-APIRequest -Method "POST" -Uri "$baseUrl/api/v1/accounts/register/" -Body $registrationData

if ($regResponse.Success) {
    Write-Host "User registration successful" -ForegroundColor Green
}
else {
    Write-Host "User registration failed: $($regResponse.Error)" -ForegroundColor Red
}

Write-Host "`n2. Testing User Login..." -ForegroundColor Yellow

$loginData = @{
    email = "123testuser@example.com"
    password = "123testpass123"
} | ConvertTo-Json

$loginResponse = Invoke-APIRequest -Method "POST" -Uri "$baseUrl/api/v1/accounts/login/" -Body $loginData

if ($loginResponse.Success) {
    Write-Host "User login successful" -ForegroundColor Green
    $accessToken = $loginResponse.Data.tokens.access
}
else {
    Write-Host "User login failed: $($loginResponse.Error)" -ForegroundColor Red
    $accessToken = $null
}

# Set up authorization header for authenticated requests
$authHeaders = @{
    "Authorization" = "Bearer $accessToken"
}

Write-Host "`n3. Testing User Profile Retrieval..." -ForegroundColor Yellow

if ($accessToken) {
    $profileResponse = Invoke-APIRequest -Method "GET" -Uri "$baseUrl/api/v1/accounts/profile/" -Headers $authHeaders
    
    if ($profileResponse.Success) {
        Write-Host "Profile retrieval successful" -ForegroundColor Green
        Write-Host "User: $($profileResponse.Data.email)" -ForegroundColor Cyan
    }
    else {
        Write-Host "Profile retrieval failed: $($profileResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping profile test - no access token" -ForegroundColor Red
}

Write-Host "`n4. Testing Profile Update..." -ForegroundColor Yellow

if ($accessToken) {
    $updateData = @{
        first_name = "Updated"
        last_name = "Name"
        bio = "Updated bio from PowerShell test"
        email_notifications = $true
        marketing_emails = $false
    } | ConvertTo-Json
    
    $updateResponse = Invoke-APIRequest -Method "PATCH" -Uri "$baseUrl/api/v1/accounts/profile/" -Headers $authHeaders -Body $updateData
    
    if ($updateResponse.Success) {
        Write-Host "Profile update successful" -ForegroundColor Green
    }
    else {
        Write-Host "Profile update failed: $($updateResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping profile update test - no access token" -ForegroundColor Red
}

Write-Host "`n5. Testing User Stats..." -ForegroundColor Yellow

if ($accessToken) {
    $statsResponse = Invoke-APIRequest -Method "GET" -Uri "$baseUrl/api/v1/accounts/stats/" -Headers $authHeaders
    
    if ($statsResponse.Success) {
        Write-Host "User stats retrieval successful" -ForegroundColor Green
    }
    else {
        Write-Host "User stats failed: $($statsResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping stats test - no access token" -ForegroundColor Red
}

Write-Host "`n6. Testing Password Change..." -ForegroundColor Yellow

if ($accessToken) {
    $passwordData = @{
        current_password = "123testpass123"
        new_password = "newpass123"
        new_password_confirm = "newpass123"
    } | ConvertTo-Json
    
    $passwordResponse = Invoke-APIRequest -Method "POST" -Uri "$baseUrl/api/v1/accounts/password/change/" -Headers $authHeaders -Body $passwordData
    
    if ($passwordResponse.Success) {
        Write-Host "Password change successful" -ForegroundColor Green
    }
    else {
        Write-Host "Password change failed: $($passwordResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping password change test - no access token" -ForegroundColor Red
}

Write-Host "`n7. Testing Health Check..." -ForegroundColor Yellow

$healthResponse = Invoke-APIRequest -Method "GET" -Uri "$baseUrl/api/v1/accounts/health/"

if ($healthResponse.Success) {
    Write-Host "Health check successful" -ForegroundColor Green
    Write-Host "Status: $($healthResponse.Data.status)" -ForegroundColor Cyan
}
else {
    Write-Host "Health check failed: $($healthResponse.Error)" -ForegroundColor Red
}

Write-Host "`n8. Testing User Logout..." -ForegroundColor Yellow

if ($accessToken) {
    $logoutResponse = Invoke-APIRequest -Method "POST" -Uri "$baseUrl/api/v1/accounts/logout/" -Headers $authHeaders
    
    if ($logoutResponse.Success) {
        Write-Host "User logout successful" -ForegroundColor Green
    }
    else {
        Write-Host "User logout failed: $($logoutResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping logout test - no access token" -ForegroundColor Red
}

Write-Host "`nAccounts package testing completed!" -ForegroundColor Green
Write-Host "Note: Make sure Django development server is running on http://127.0.0.1:8000" -ForegroundColor Yellow



