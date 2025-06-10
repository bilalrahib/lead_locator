Write-Host "`n4a. Testing Profile Details Update..." -ForegroundColor Yellow

if ($accessToken) {
    $profileData = @{
        business_type = "small_business"
        years_in_business = 5
        number_of_machines = 10
        city = "Test City"
        state = "Test State"
        zip_code = "12345"
    } | ConvertTo-Json
    
    $profileResponse = Invoke-APIRequest -Method "POST" -Uri "$baseUrl/api/v1/accounts/profile/details/" -Headers $authHeaders -Body $profileData
    
    if ($profileResponse.Success) {
        Write-Host "Profile details update successful" -ForegroundColor Green
    }
    else {
        Write-Host "Profile details update failed: $($profileResponse.Error)" -ForegroundColor Red
    }
}
else {
    Write-Host "Skipping profile details test - no access token" -ForegroundColor Red
}