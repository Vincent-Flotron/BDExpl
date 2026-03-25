<#
.SYNOPSIS
    Tests network connection to a specified host and port.

.DESCRIPTION
    This script tests network connectivity to a specified host and port using Test-NetConnection.

.PARAMETER ComputerName
    The hostname or IP address to test connection to.

.PARAMETER Port
    The port number to test connection to.

.EXAMPLE
    .\test_connection.ps1 -ComputerName "10.223.45.234" -Port 5432
    Tests connection to 10.223.45.234 on port 5432

.EXAMPLE
    .\test_connection.ps1 -ComputerName "example.com" -Port 80
    Tests connection to example.com on port 80
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,

    [Parameter(Mandatory=$true)]
    [int]$Port
)

Test-NetConnection -ComputerName $ComputerName -Port $Port