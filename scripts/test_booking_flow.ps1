# Complete End-to-End Booking Flow Test

# Get the project root (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
Set-Location $BaseDir

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TESTING COMPLETE BOOKING FLOW        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

$conversationId = $null

# Test 1: Greeting
Write-Host "1. Testing Greeting..." -ForegroundColor Yellow
$body = @{ message = "hi"; user_id = "e2e_test_user" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
$conversationId = $response.conversation_id
Write-Host "   Response: $($response.message.Substring(0, 60))..." -ForegroundColor Green

# Test 2: Doctor information
Write-Host "`n2. Testing Doctor Info..." -ForegroundColor Yellow
$body = @{ message = "tell me about dermatology"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
Write-Host "   Response: $($response.message)" -ForegroundColor Green

# Test 3: Pronoun reference
Write-Host "`n3. Testing Pronoun Resolution (tell me more about her)..." -ForegroundColor Yellow
$body = @{ message = "tell me more about her"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
if ($response.message -like "*Aditi Tomar*") {
    Write-Host "   ✓ FIXED: Pronoun resolved correctly!" -ForegroundColor Green
} else {
    Write-Host "   Response: $($response.message)" -ForegroundColor Yellow
}

# Test 4: Book appointment
Write-Host "`n4. Testing Booking Flow..." -ForegroundColor Yellow
$body = @{ message = "book appointment with her"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
Write-Host "   Response: $($response.message)" -ForegroundColor Green

# Test 5: Provide date and time
Write-Host "`n5. Providing Date and Time..." -ForegroundColor Yellow
$body = @{ message = "tomorrow at 2pm"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
Write-Host "   Response: $($response.message.Substring(0, 80))..." -ForegroundColor Green

# Test 6: Provide name and phone
Write-Host "`n6. Providing Name and Phone..." -ForegroundColor Yellow
$body = @{ message = "My name is Test User and phone is 9876543210"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
Write-Host "   Response:" -ForegroundColor Cyan
Write-Host "   $($response.message)" -ForegroundColor White

# Test 7: Confirm booking
Write-Host "`n7. Confirming Booking..." -ForegroundColor Yellow
$body = @{ message = "yes"; user_id = "e2e_test_user"; conversation_id = $conversationId } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8003/api/v1/chat/" -Method Post -Body $body -ContentType "application/json"
if ($response.message -like "*booked successfully*" -or $response.message -like "*✅*") {
    Write-Host "   ✓ BOOKING SUCCESSFUL!" -ForegroundColor Green
    Write-Host "   Response:" -ForegroundColor Cyan
    Write-Host "   $($response.message)" -ForegroundColor White
} else {
    Write-Host "   Response: $($response.message)" -ForegroundColor Yellow
}

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST COMPLETE                         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan
