Write-Host "Testing Admin Data Creation..." -ForegroundColor Green

# Test if setup_initial_data worked
try {
    $homepage = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/core/homepage/"
    
    if ($homepage.subscription_plans -and $homepage.subscription_plans.Count -gt 0) {
        Write-Host "Subscription Plans: $($homepage.subscription_plans.Count) plans created" -ForegroundColor Green
        
        foreach ($plan in $homepage.subscription_plans) {
            Write-Host "  - $($plan.name): $($plan.price)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "Subscription Plans: No plans found - run 'python manage.py setup_initial_data'" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error testing admin data: $($_.Exception.Message)" -ForegroundColor Red
}