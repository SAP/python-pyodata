/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements. See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.olingo.server.sample;

import java.io.IOException;
import java.util.ArrayList;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import org.apache.olingo.commons.api.edmx.EdmxReference;
import org.apache.olingo.server.api.OData;
import org.apache.olingo.server.api.ODataHttpHandler;
import org.apache.olingo.server.api.ServiceMetadata;
import org.apache.olingo.server.sample.data.DataProvider;
import org.apache.olingo.server.sample.edmprovider.CarsEdmProvider;
import org.apache.olingo.server.sample.processor.CarsProcessor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class CarsServlet extends HttpServlet {

  private static final long serialVersionUID = 1L;
  private static final Logger LOG = LoggerFactory.getLogger(CarsServlet.class);

  @Override
  protected void service(final HttpServletRequest req, final HttpServletResponse resp)
      throws ServletException, IOException {
    try {
      HttpSession session = req.getSession(true);
      DataProvider dataProvider = (DataProvider) session.getAttribute(DataProvider.class.getName());
      if (dataProvider == null) {
        dataProvider = new DataProvider();
        session.setAttribute(DataProvider.class.getName(), dataProvider);
        LOG.info("Created new data provider.");
      }

      OData odata = OData.newInstance();
      ServiceMetadata edm = odata.createServiceMetadata(new CarsEdmProvider(), new ArrayList<EdmxReference>());
      ODataHttpHandler handler = odata.createHandler(edm);
      handler.register(new CarsProcessor(dataProvider));
      handler.process(req, resp);
    } catch (RuntimeException e) {
      LOG.error("Server Error", e);
      throw new ServletException(e);
    }
  }
}
