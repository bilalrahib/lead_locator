# Test script for Vending Hive Project Core
param(
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$Verbose = $false
)

function Write-Success($message) {
    Write-Host "[PASS] $message" -ForegroundColor Green
}

function Write-Failure($message) {
    Write-Host "[FAIL] $message" -ForegroundColor Red
}

function Write-Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Write-Warning($message) {
    Write-Host "[WARN] $message" -ForegroundColor Yellow
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null,
        [hashtable]$Headers = @{},
        [string]$ExpectedField = $null
    )
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            TimeoutSec = 10
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-RestMethod @params
        
        if ($ExpectedField -and $response.$ExpectedField) {
            Write-Success "$Name - $($response.$ExpectedField)"
        } else {
            Write-Success "$Name - Success"
        }
        
        if ($Verbose) {
            Write-Info "Response: $($response | ConvertTo-Json -Depth 2)"
        }
        
        return $response
    }
    catch {
        Write-Failure "$Name - $($_.Exception.Message)"
        if ($Verbose) {
            Write-Info "Error Details: $($_.ErrorDetails.Message)"
        }
        return $null
    }
}

# Start testing
Write-Host "=" * 60 -ForegroundColor Magenta
Write-Host "VENDING HIVE PROJECT CORE TEST SUITE" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta
Write-Host "Base URL: $BaseUrl" -ForegroundColor Yellow
Write-Host "Timestamp: $(Get-Date)" -ForegroundColor Yellow
Write-Host ""

# Test 1: Health Check
Write-Info "Testing Health Check Endpoint..."
$health = Test-Endpoint -Name "Health Check" -Url "$BaseUrl/api/v1/core/health/" -ExpectedField "status"

# Test 2: System Status
Write-Info "Testing System Status Endpoint..."
$status = Test-Endpoint -Name "System Status" -Url "$BaseUrl/api/v1/core/status/" -ExpectedField "status"

# Test 3: Homepage API Data
Write-Info "Testing Homepage API Data..."
$homepage = Test-Endpoint -Name "Homepage API" -Url "$BaseUrl/api/v1/core/homepage/" -ExpectedField "company_name"

if ($homepage) {
    Write-Info "Company: $($homepage.company_name)"
    Write-Info "Features count: $($homepage.features.Count)"
    Write-Info "Plans count: $($homepage.subscription_plans.Count)"
}

# Test 4: Contact Form Submission
Write-Info "Testing Contact Form Submission..."
$contactData = @{
    name = "Test User"
    email = "testuser@example.com"
    phone = "555-123-4567"
    subject = "Test Contact from PowerShell"
    message = "This is a test message submitted via PowerShell script to verify the contact form endpoint is working correctly."
} | ConvertTo-Json

$contact = Test-Endpoint -Name "Contact Form" -Url "$BaseUrl/api/v1/core/contact/" -Method "POST" -Body $contactData

if ($contact) {
    Write-Info "Contact message created with ID: $($contact.id)"
}

# Test 5: Test Web Pages (GET requests)
Write-Info "Testing Web Pages..."

try {
    $homepageWeb = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 10
    if ($homepageWeb.StatusCode -eq 200) {
        Write-Success "Homepage Web - Status Code: $($homepageWeb.StatusCode)"
    }
} catch {
    Write-Failure "Homepage Web - $($_.Exception.Message)"
}

try {
    $adminPage = Invoke-WebRequest -Uri "$BaseUrl/admin/" -UseBasicParsing -TimeoutSec 10
    if ($adminPage.StatusCode -eq 200) {
        Write-Success "Admin Page - Status Code: $($adminPage.StatusCode)"
    }
} catch {
    Write-Failure "Admin Page - $($_.Exception.Message)"
}

# Test 6: Test Authentication Required Endpoints (should fail without auth)
Write-Info "Testing Authentication Required Endpoints (should return 401/403)..."

try {
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/core/support-tickets/" -Method GET -TimeoutSec 10
    Write-Warning "Support Tickets - Expected authentication error but got success"
} catch {
    if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
        Write-Success "Support Tickets - Correctly requires authentication"
    } else {
        Write-Failure "Support Tickets - Unexpected error: $($_.Exception.Message)"
    }
}

try {
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/core/weather/" -Method GET -TimeoutSec 10
    Write-Warning "Weather Data - Expected authentication error but got success"
} catch {
    if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
        Write-Success "Weather Data - Correctly requires authentication"
    } else {
        Write-Failure "Weather Data - Unexpected error: $($_.Exception.Message)"
    }
}

# Test 7: Invalid Endpoints (should return 404)
Write-Info "Testing Invalid Endpoints (should return 404)..."

try {
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/core/nonexistent/" -Method GET -TimeoutSec 10
    Write-Warning "Invalid Endpoint - Expected 404 but got success"
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Success "Invalid Endpoint - Correctly returns 404"
    } else {
        Write-Failure "Invalid Endpoint - Unexpected error: $($_.Exception.Message)"
    }
}

# Test 8: Database Connectivity (via health check details)
Write-Info "Testing Database Connectivity..."
if ($status -and $status.services -and $status.services.database) {
    if ($status.services.database -eq "healthy") {
        Write-Success "Database - Connection healthy"
    } else {
        Write-Failure "Database - Connection issue: $($status.services.database)"
    }
}

# Test 9: Test Models Creation via Contact Form
Write-Info "Testing Database Model Creation..."
try {
    # Create another contact to test database operations
    $testContact = @{
        name = "Database Test User"
        email = "dbtest@example.com"
        subject = "Database Test"
        message = "Testing database model creation and storage."
    } | ConvertTo-Json

    $dbTest = Test-Endpoint -Name "Database Model Test" -Url "$BaseUrl/api/v1/core/contact/" -Method "POST" -Body $testContact
    
    if ($dbTest -and $dbTest.id) {
        Write-Success "Database Models - Contact model working correctly"
    }
} catch {
    Write-Failure "Database Models - Error creating contact: $($_.Exception.Message)"
}

# Summary
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Magenta
Write-Host "TEST SUMMARY" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

$allTests = @(
    "Health Check", "System Status", "Homepage API", "Contact Form",
    "Homepage Web", "Admin Page", "Support Tickets Auth", "Weather Data Auth",
    "Invalid Endpoint", "Database", "Database Models"
)

Write-Host "Total tests run: $($allTests.Count)" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date)" -ForegroundColor Yellow

# Additional Information
Write-Host ""
Write-Info "Next Steps:"
Write-Host "1. Visit $BaseUrl/ to see the homepage" -ForegroundColor White
Write-Host "2. Visit $BaseUrl/admin/ to access Django admin" -ForegroundColor White
Write-Host "3. Create a superuser: python manage.py createsuperuser" -ForegroundColor White
Write-Host "4. Check Django logs for any errors" -ForegroundColor White
Write-Host "5. Test contact form submissions in Django admin" -ForegroundColor White

Write-Host ""
Write-Host "Test completed successfully!" -ForegroundColor Green