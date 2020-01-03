<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>

<!--
  Licensed to the Apache Software Foundation (ASF) under one
         or more contributor license agreements.  See the NOTICE file
         distributed with this work for additional information
         regarding copyright ownership.  The ASF licenses this file
         to you under the Apache License, Version 2.0 (the
         "License"); you may not use this file except in compliance
         with the License.  You may obtain a copy of the License at
  
           http://www.apache.org/licenses/LICENSE-2.0
  
         Unless required by applicable law or agreed to in writing,
         software distributed under the License is distributed on an
         "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
         KIND, either express or implied.  See the License for the
         specific language governing permissions and limitations
         under the License.
-->

<!DOCTYPE html>
<html>
<head>
 <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
 <title>Apache Olingo - OData 4.0</title>
 <link type="text/css" rel="stylesheet" href="css/olingo.css">
</head>

<body>
  <div class="logo">
    <img height="40" src="img/OlingoOrangeTM.png" />
  </div>
  <h1>Olingo OData 4.0</h1>
  <hr>
  <h2>Cars Sample Service</h2>
  <ul>
    <li><a href="cars.svc/">Service Document</a></li>
    <li><a href="cars.svc/$metadata">Metadata</a></li>
    <li>Entity Set: <a href="cars.svc/Cars">Cars</a></li>
    <li>Entity: <a href="cars.svc/Cars(1)">Cars(1)</a></li>
    <li>Primitive Property: <a href="cars.svc/Cars(1)/Price">Cars(1)/Price</a></li>
  </ul>
  <hr>
  <div class="version">
    <% String version = "gen/version.html";
      try {
     %>
    <jsp:include page='<%=version%>' />
    <%} catch (Exception e) {
     %>
    <p>IDE Build</p>
    <%}%>
  </div>
</body>
</html>
