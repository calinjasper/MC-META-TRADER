' Excel VBA Example - Sending Signals to Trading Platform
'
' This example shows how to send trading signals from Excel
' to the trading platform's signal server using HTTP requests.
'
' Requirements:
' - Excel with Microsoft XML library enabled (Tools > References > Microsoft XML)
' - Trading platform signal server running on localhost:8080

Option Explicit

' Signal Server Configuration
Const SignalServerURL As String = "http://localhost:8080/signal"

' Function to send signal via HTTP GET (Format 1 or 2)
Function SendSignalGET(Symbol As String, Action As String, Quantity As Double, _
                       Optional SL As Double = 0, Optional TP As Double = 0) As String
    Dim URL As String
    Dim XMLHttp As Object
    Dim Response As String
    
    ' Build URL
    URL = SignalServerURL & "?symbol=" & Symbol & _
          "&action=" & Action & _
          "&qty=" & Quantity
    
    If SL > 0 Then
        URL = URL & "&sl=" & SL
    End If
    If TP > 0 Then
        URL = URL & "&tp=" & TP
    End If
    
    ' Create HTTP request
    Set XMLHttp = CreateObject("MSXML2.XMLHTTP")
    
    On Error GoTo ErrorHandler
    
    XMLHttp.Open "GET", URL, False
    XMLHttp.send
    
    Response = XMLHttp.responseText
    SendSignalGET = Response
    
    Set XMLHttp = Nothing
    Exit Function
    
ErrorHandler:
    SendSignalGET = "Error: " & Err.Description
    Set XMLHttp = Nothing
End Function

' Function to send signal via HTTP POST (Format 3)
Function SendSignalPOST(Symbol As String, Action As String, Quantity As Double, _
                        Optional SL As Double = 0, Optional TP As Double = 0, _
                        Optional Comment As String = "Excel Signal") As String
    Dim URL As String
    Dim XMLHttp As Object
    Dim JSON As String
    Dim Response As String
    
    ' Build JSON payload
    JSON = "{" & _
           """symbol"":""" & Symbol & """," & _
           """action"":""" & Action & """," & _
           """quantity"":" & Quantity & "," & _
           """stop_loss"":" & SL & "," & _
           """take_profit"":" & TP & "," & _
           """comment"":""" & Comment & """" & _
           "}"
    
    ' Create HTTP request
    Set XMLHttp = CreateObject("MSXML2.XMLHTTP")
    
    On Error GoTo ErrorHandler
    
    XMLHttp.Open "POST", SignalServerURL, False
    XMLHttp.setRequestHeader "Content-Type", "application/json"
    XMLHttp.send JSON
    
    Response = XMLHttp.responseText
    SendSignalPOST = Response
    
    Set XMLHttp = Nothing
    Exit Function
    
ErrorHandler:
    SendSignalPOST = "Error: " & Err.Description
    Set XMLHttp = Nothing
End Function

' Example Subroutine: Send BUY Signal
Sub SendBuySignal()
    Dim Symbol As String
    Dim Quantity As Double
    Dim SL As Double
    Dim TP As Double
    Dim Result As String
    
    ' Set parameters
    Symbol = "EURUSD"
    Quantity = 0.01
    SL = 1.0800
    TP = 1.0900
    
    ' Send signal
    Result = SendSignalPOST(Symbol, "BUY", Quantity, SL, TP, "Excel BUY Signal")
    
    ' Display result
    MsgBox "Signal Result: " & Result
End Sub

' Example Subroutine: Send SELL Signal
Sub SendSellSignal()
    Dim Symbol As String
    Dim Quantity As Double
    Dim Result As String
    
    Symbol = "GBPUSD"
    Quantity = 0.01
    
    Result = SendSignalPOST(Symbol, "SELL", Quantity, , , "Excel SELL Signal")
    
    MsgBox "Signal Result: " & Result
End Sub

' Example Subroutine: Close All Positions
Sub CloseAllPositions()
    Dim Symbol As String
    Dim Result As String
    
    Symbol = "EURUSD"
    
    Result = SendSignalGET(Symbol, "EXIT", 0)
    
    MsgBox "Exit Result: " & Result
End Sub

' Example: Send signal from worksheet cell
' You can call this from a button or cell formula
Function SendSignalFromCell(Symbol As String, Action As String, Quantity As Double) As String
    SendSignalFromCell = SendSignalPOST(Symbol, Action, Quantity, , , "Excel Cell Signal")
End Function

